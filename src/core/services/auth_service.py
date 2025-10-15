import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
import boto3
import jwt
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_database_session
from ..models.auth import AuthConfig, User
from ..repositories.user_repository import UserRepository
from ..services.logging_service import StructuredLogger

logger = StructuredLogger("service.auth")


class TokenData(BaseModel):
    """Token validation data."""

    user_id: str
    email: str
    is_admin: bool
    roles: List[str]
    exp: int


class CognitoConfig(BaseModel):
    """AWS Cognito configuration."""

    user_pool_id: str
    client_id: str
    region: str
    jwt_secret: Optional[str] = None


class LocalAuthConfig(BaseModel):
    """Local authentication configuration."""

    jwt_secret: str
    token_expiry_hours: int = 24
    require_email_verification: bool = False


class AuthService:
    """Centralized authentication service supporting both Cognito and local auth."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_database_session()
        self.user_repo = UserRepository(self.db)
        self._current_config: Optional[AuthConfig] = None
        self._cognito_client = None
        self._jwt_secret = None

    async def get_current_config(self) -> AuthConfig:
        """Get the current authentication configuration."""
        if self._current_config is None:
            # Load from database or environment
            config_record = self.db.query(AuthConfig).first()
            if config_record:
                self._current_config = config_record
            else:
                # Create default local auth config
                self._current_config = AuthConfig(
                    provider_type="local",
                    enabled=True,
                    config={
                        "jwt_secret": secrets.token_hex(32),
                        "token_expiry_hours": 24,
                        "require_email_verification": False,
                    },
                )
                self.db.add(self._current_config)
                self.db.commit()

        return self._current_config

    async def update_config(
        self, provider_type: str, enabled: bool, config: Dict[str, Any]
    ) -> None:
        """Update authentication configuration."""
        try:
            current_config = await self.get_current_config()

            # Validate provider type
            if provider_type not in ["cognito", "local"]:
                raise ValueError("Invalid provider type")

            # Validate configuration based on provider
            if provider_type == "cognito":
                self._validate_cognito_config(config)
            else:
                self._validate_local_config(config)

            # Update configuration
            current_config.provider_type = provider_type
            current_config.enabled = enabled
            current_config.config = config
            current_config.updated_at = datetime.utcnow()

            self.db.commit()

            # Reset cached values
            self._current_config = current_config
            self._cognito_client = None
            self._jwt_secret = None

            logger.info(
                "Auth configuration updated",
                {"provider_type": provider_type, "enabled": enabled},
            )

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update auth config", {"error": str(e)})
            raise

    def _validate_cognito_config(self, config: Dict[str, Any]) -> None:
        """Validate Cognito configuration."""
        required_fields = ["user_pool_id", "client_id", "region"]
        for field in required_fields:
            if field not in config or not config[field]:
                raise ValueError(f"Missing required Cognito config field: {field}")

    def _validate_local_config(self, config: Dict[str, Any]) -> None:
        """Validate local authentication configuration."""
        if "jwt_secret" not in config or not config["jwt_secret"]:
            config["jwt_secret"] = secrets.token_hex(32)

        if "token_expiry_hours" not in config:
            config["token_expiry_hours"] = 24

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user using the current provider."""
        try:
            config = await self.get_current_config()

            if not config.enabled:
                raise ValueError("Authentication is disabled")

            if config.provider_type == "cognito":
                return await self._authenticate_cognito(email, password, config.config)
            else:
                return await self._authenticate_local(email, password, config.config)

        except Exception as e:
            logger.error(
                "Authentication failed",
                {
                    "email": email,
                    "provider": (
                        config.provider_type if "config" in locals() else "unknown"
                    ),
                    "error": str(e),
                },
            )
            raise

    async def _authenticate_cognito(
        self, email: str, password: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Authenticate using AWS Cognito."""
        try:
            cognito_config = CognitoConfig(**config)

            if not self._cognito_client:
                self._cognito_client = boto3.client(
                    "cognito-idp", region_name=cognito_config.region
                )

            # Authenticate with Cognito
            response = self._cognito_client.admin_initiate_auth(
                UserPoolId=cognito_config.user_pool_id,
                ClientId=cognito_config.client_id,
                AuthFlow="ADMIN_NO_SRP_AUTH",
                AuthParameters={"USERNAME": email, "PASSWORD": password},
            )

            # Extract user information from Cognito response
            access_token = response["AuthenticationResult"]["AccessToken"]
            id_token = response["AuthenticationResult"]["IdToken"]

            # Decode the ID token to get user info
            user_info = jwt.decode(
                id_token,
                options={"verify_signature": False},  # Cognito tokens are pre-verified
            )

            # Sync user with local database
            user = await self._sync_cognito_user(user_info, access_token)

            # Generate our own JWT for internal use
            token = self._generate_jwt_token(user, config)

            logger.info(
                "Cognito authentication successful",
                {"user_id": user.id, "email": user.email},
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "is_admin": user.is_admin,
                    "roles": [role.name for role in user.roles],
                },
            }

        except Exception as e:
            logger.error(
                "Cognito authentication failed", {"email": email, "error": str(e)}
            )
            raise

    async def _authenticate_local(
        self, email: str, password: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Authenticate using local credentials."""
        try:
            _local_config = LocalAuthConfig(**config)

            # Find user in database
            user = await self.user_repo.get_by_email(email)
            if not user:
                raise ValueError("Invalid credentials")

            # Verify password
            if not bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                raise ValueError("Invalid credentials")

            # Check if user is active
            if not user.is_active:
                raise ValueError("User account is disabled")

            # Generate JWT token
            token = self._generate_jwt_token(user, config)

            logger.info(
                "Local authentication successful",
                {"user_id": user.id, "email": user.email},
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "is_admin": user.is_admin,
                    "roles": [role.name for role in user.roles],
                },
            }

        except Exception as e:
            logger.error(
                "Local authentication failed", {"email": email, "error": str(e)}
            )
            raise

    async def _sync_cognito_user(
        self, cognito_user_info: Dict[str, Any], access_token: str
    ) -> User:
        """Sync Cognito user with local database."""
        try:
            email = cognito_user_info.get("email")
            name = cognito_user_info.get("name", email)
            cognito_user_id = cognito_user_info.get("sub")

            # Check if user exists locally
            user = await self.user_repo.get_by_email(email)
            if not user:
                # Create new user
                user = await self.user_repo.create_user(
                    email=email,
                    name=name,
                    password_hash="",  # Not used for Cognito users
                    is_admin=False,
                    provider="cognito",
                    provider_user_id=cognito_user_id,
                )
                logger.info(
                    "New Cognito user created", {"user_id": user.id, "email": email}
                )
            else:
                # Update existing user
                user.name = name
                user.last_login = datetime.utcnow()
                user.provider = "cognito"
                user.provider_user_id = cognito_user_id
                self.db.commit()

            return user

        except Exception as e:
            logger.error("Failed to sync Cognito user", {"error": str(e)})
            raise

    def _generate_jwt_token(self, user: User, config: Dict[str, Any]) -> str:
        """Generate JWT token for authenticated user."""
        try:
            jwt_secret = config.get("jwt_secret")
            if not jwt_secret:
                raise ValueError("JWT secret not configured")

            expiry_hours = config.get("token_expiry_hours", 24)
            expiry = datetime.utcnow() + timedelta(hours=expiry_hours)

            payload = {
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "is_admin": user.is_admin,
                "roles": [role.name for role in user.roles],
                "exp": expiry.timestamp(),
                "iat": datetime.utcnow().timestamp(),
            }

            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            return token

        except Exception as e:
            logger.error("Failed to generate JWT token", {"error": str(e)})
            raise

    async def verify_token(self, token: str) -> User:
        """Verify and decode a JWT token."""
        try:
            config = await self.get_current_config()
            jwt_secret = config.config.get("jwt_secret")

            if not jwt_secret:
                raise ValueError("JWT secret not configured")

            # Decode token
            payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])

            # Extract user data
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload")

            # Get user from database
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            if not user.is_active:
                raise ValueError("User account is disabled")

            return user

        except JWTError as e:
            logger.warning("JWT verification failed", {"error": str(e)})
            raise ValueError("Invalid or expired token")
        except Exception as e:
            logger.error("Token verification failed", {"error": str(e)})
            raise

    async def create_local_user(
        self, email: str, password: str, name: str, is_admin: bool = False
    ) -> User:
        """Create a new local user account."""
        try:
            config = await self.get_current_config()

            if config.provider_type != "local":
                raise ValueError("Local user creation not available in Cognito mode")

            # Hash password
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            # Create user
            user = await self.user_repo.create_user(
                email=email,
                name=name,
                password_hash=password_hash,
                is_admin=is_admin,
                provider="local",
            )

            logger.info(
                "Local user created",
                {"user_id": user.id, "email": email, "is_admin": is_admin},
            )

            return user

        except Exception as e:
            logger.error(
                "Failed to create local user", {"email": email, "error": str(e)}
            )
            raise

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """Change user password (local auth only)."""
        try:
            config = await self.get_current_config()

            if config.provider_type != "local":
                raise ValueError("Password change not available in Cognito mode")

            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            # Verify old password
            if not bcrypt.checkpw(
                old_password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                raise ValueError("Invalid current password")

            # Hash new password
            new_password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            # Update user
            await self.user_repo.update_user(
                user_id, {"password_hash": new_password_hash}
            )

            logger.info("Password changed", {"user_id": user_id})
            return True

        except Exception as e:
            logger.error(
                "Failed to change password", {"user_id": user_id, "error": str(e)}
            )
            raise

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an authentication token."""
        try:
            config = await self.get_current_config()

            if config.provider_type == "cognito":
                return await self._refresh_cognito_token(refresh_token, config.config)
            else:
                # For local auth, we might implement refresh tokens differently
                # For now, just verify the existing token
                user = await self.verify_token(refresh_token)
                new_token = self._generate_jwt_token(user, config.config)

                return {"access_token": new_token, "token_type": "bearer"}

        except Exception as e:
            logger.error("Token refresh failed", {"error": str(e)})
            raise

    async def _refresh_cognito_token(
        self, refresh_token: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refresh Cognito token."""
        try:
            cognito_config = CognitoConfig(**config)

            if not self._cognito_client:
                self._cognito_client = boto3.client(
                    "cognito-idp", region_name=cognito_config.region
                )

            response = self._cognito_client.admin_initiate_auth(
                UserPoolId=cognito_config.user_pool_id,
                ClientId=cognito_config.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": refresh_token},
            )

            access_token = response["AuthenticationResult"]["AccessToken"]
            id_token = response["AuthenticationResult"]["IdToken"]

            return {
                "access_token": access_token,
                "id_token": id_token,
                "token_type": "bearer",
            }

        except Exception as e:
            logger.error("Cognito token refresh failed", {"error": str(e)})
            raise

    async def logout_user(self, user_id: str, token: str) -> bool:
        """Log out a user (invalidate token)."""
        try:
            config = await self.get_current_config()

            if config.provider_type == "cognito":
                # For Cognito, we could revoke the token
                # This requires additional implementation
                pass
            else:
                # For local auth, we might maintain a token blacklist
                # This requires additional implementation
                pass

            logger.info("User logged out", {"user_id": user_id})
            return True

        except Exception as e:
            logger.error("Logout failed", {"user_id": user_id, "error": str(e)})
            raise

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions based on roles."""
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return []

            permissions = set()
            for role in user.roles:
                permissions.update(role.permissions)

            return list(permissions)

        except Exception as e:
            logger.error(
                "Failed to get user permissions", {"user_id": user_id, "error": str(e)}
            )
            raise

    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        try:
            permissions = await self.get_user_permissions(user_id)
            return permission in permissions or await self.is_admin(user_id)

        except Exception as e:
            logger.error(
                "Permission check failed",
                {"user_id": user_id, "permission": permission, "error": str(e)},
            )
            return False

    async def is_admin(self, user_id: str) -> bool:
        """Check if user is an admin."""
        try:
            user = await self.user_repo.get_by_id(user_id)
            return user.is_admin if user else False

        except Exception as e:
            logger.error("Admin check failed", {"user_id": user_id, "error": str(e)})
            return False
