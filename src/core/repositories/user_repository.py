from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from ..models.auth import (
    User, Role, Permission, UserSession, AuthConfig,
    UserStatus, AuthProvider, user_roles, role_permissions
)
from ..database import get_database_session
from ..services.logging_service import StructuredLogger

logger = StructuredLogger("repository.user")

class UserRepository:
    """Repository for managing user data and authentication."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_database_session()

    async def create_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        is_admin: bool = False,
        provider: str = "local",
        provider_user_id: Optional[str] = None
    ) -> User:
        """Create a new user."""
        try:
            user = User(
                id=str(uuid.uuid4()),
                email=email.lower(),
                name=name,
                password_hash=password_hash,
                is_admin=is_admin,
                provider=provider,
                provider_user_id=provider_user_id,
                is_active=True,
                is_verified=provider != "local",  # External providers are pre-verified
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )

            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            # Assign default role
            if is_admin:
                await self.assign_role(user.id, "admin")
            else:
                await self.assign_role(user.id, "user")

            logger.info("User created", {
                "user_id": user.id,
                "email": email,
                "provider": provider,
                "is_admin": is_admin
            })

            return user

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create user", {
                "email": email,
                "error": str(e)
            })
            raise

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID with roles and permissions."""
        try:
            user = self.db.query(User).options(
                joinedload(User.roles).joinedload(Role.permissions)
            ).filter(User.id == user_id).first()

            if user:
                logger.debug("User retrieved by ID", {"user_id": user_id})

            return user

        except Exception as e:
            logger.error("Failed to get user by ID", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email with roles and permissions."""
        try:
            user = self.db.query(User).options(
                joinedload(User.roles).joinedload(Role.permissions)
            ).filter(User.email == email.lower()).first()

            if user:
                logger.debug("User retrieved by email", {"email": email})

            return user

        except Exception as e:
            logger.error("Failed to get user by email", {
                "email": email,
                "error": str(e)
            })
            raise

    async def get_by_provider_id(self, provider: str, provider_user_id: str) -> Optional[User]:
        """Get a user by provider and provider user ID."""
        try:
            user = self.db.query(User).options(
                joinedload(User.roles).joinedload(Role.permissions)
            ).filter(
                and_(
                    User.provider == provider,
                    User.provider_user_id == provider_user_id
                )
            ).first()

            return user

        except Exception as e:
            logger.error("Failed to get user by provider ID", {
                "provider": provider,
                "provider_user_id": provider_user_id,
                "error": str(e)
            })
            raise

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user information."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return None

            # Update allowed fields
            for field, value in update_data.items():
                if hasattr(user, field) and field not in ['id', 'created_at']:
                    setattr(user, field, value)

            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)

            logger.info("User updated", {
                "user_id": user_id,
                "updated_fields": list(update_data.keys())
            })

            return user

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update user", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete by deactivating)."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False

            user.is_active = False
            user.status = UserStatus.INACTIVE
            user.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info("User deleted (deactivated)", {"user_id": user_id})
            return True

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to delete user", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None,
        provider_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """List users with filtering and pagination."""
        try:
            query = self.db.query(User).options(
                joinedload(User.roles)
            )

            # Apply filters
            if status_filter:
                query = query.filter(User.status == status_filter)

            if provider_filter:
                query = query.filter(User.provider == provider_filter)

            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        User.email.ilike(search_term),
                        User.name.ilike(search_term)
                    )
                )

            # Apply pagination
            users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()

            logger.debug("Users listed", {
                "count": len(users),
                "skip": skip,
                "limit": limit,
                "filters": {
                    "status": status_filter,
                    "provider": provider_filter,
                    "search": search
                }
            })

            return users

        except Exception as e:
            logger.error("Failed to list users", {"error": str(e)})
            raise

    async def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False

            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                logger.warning("Role not found", {"role_name": role_name})
                return False

            # Check if user already has this role
            if role in user.roles:
                return True

            user.roles.append(role)
            self.db.commit()

            logger.info("Role assigned to user", {
                "user_id": user_id,
                "role_name": role_name
            })

            return True

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to assign role", {
                "user_id": user_id,
                "role_name": role_name,
                "error": str(e)
            })
            raise

    async def remove_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False

            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                return False

            if role in user.roles:
                user.roles.remove(role)
                self.db.commit()

                logger.info("Role removed from user", {
                    "user_id": user_id,
                    "role_name": role_name
                })

            return True

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to remove role", {
                "user_id": user_id,
                "role_name": role_name,
                "error": str(e)
            })
            raise

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user through their roles."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return []

            permissions = set()
            for role in user.roles:
                for permission in role.permissions:
                    permissions.add(permission.name)

            return list(permissions)

        except Exception as e:
            logger.error("Failed to get user permissions", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    async def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        refresh_token_hash: Optional[str] = None
    ) -> UserSession:
        """Create a new user session."""
        try:
            session = UserSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token_hash=token_hash,
                refresh_token_hash=refresh_token_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                is_active=True
            )

            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

            logger.info("User session created", {
                "user_id": user_id,
                "session_id": session.id,
                "ip_address": ip_address
            })

            return session

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create session", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    async def get_session(self, token_hash: str) -> Optional[UserSession]:
        """Get a session by token hash."""
        try:
            session = self.db.query(UserSession).filter(
                and_(
                    UserSession.token_hash == token_hash,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            ).first()

            if session:
                # Update last accessed time
                session.last_accessed = datetime.utcnow()
                self.db.commit()

            return session

        except Exception as e:
            logger.error("Failed to get session", {"error": str(e)})
            raise

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a user session."""
        try:
            session = self.db.query(UserSession).filter(
                UserSession.id == session_id
            ).first()

            if not session:
                return False

            session.is_active = False
            session.revoked_at = datetime.utcnow()
            self.db.commit()

            logger.info("Session revoked", {"session_id": session_id})
            return True

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to revoke session", {
                "session_id": session_id,
                "error": str(e)
            })
            raise

    async def revoke_user_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Revoke all sessions for a user."""
        try:
            query = self.db.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )

            if except_session_id:
                query = query.filter(UserSession.id != except_session_id)

            sessions = query.all()
            revoked_count = 0

            for session in sessions:
                session.is_active = False
                session.revoked_at = datetime.utcnow()
                revoked_count += 1

            self.db.commit()

            logger.info("User sessions revoked", {
                "user_id": user_id,
                "revoked_count": revoked_count
            })

            return revoked_count

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to revoke user sessions", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            expired_sessions = self.db.query(UserSession).filter(
                or_(
                    UserSession.expires_at <= datetime.utcnow(),
                    and_(
                        UserSession.is_active == True,
                        UserSession.last_accessed <= datetime.utcnow() - timedelta(days=30)
                    )
                )
            ).all()

            cleanup_count = 0
            for session in expired_sessions:
                session.is_active = False
                if not session.revoked_at:
                    session.revoked_at = datetime.utcnow()
                cleanup_count += 1

            self.db.commit()

            logger.info("Expired sessions cleaned up", {
                "cleanup_count": cleanup_count
            })

            return cleanup_count

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to cleanup expired sessions", {"error": str(e)})
            raise

    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[UserSession]:
        """Get all sessions for a user."""
        try:
            query = self.db.query(UserSession).filter(UserSession.user_id == user_id)

            if active_only:
                query = query.filter(
                    and_(
                        UserSession.is_active == True,
                        UserSession.expires_at > datetime.utcnow()
                    )
                )

            sessions = query.order_by(desc(UserSession.last_accessed)).all()

            return sessions

        except Exception as e:
            logger.error("Failed to get user sessions", {
                "user_id": user_id,
                "error": str(e)
            })
            raise

    # Role and Permission management methods

    async def create_role(self, name: str, description: Optional[str] = None) -> Role:
        """Create a new role."""
        try:
            role = Role(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                created_at=datetime.utcnow()
            )

            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)

            logger.info("Role created", {"role_id": role.id, "name": name})

            return role

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create role", {"name": name, "error": str(e)})
            raise

    async def create_permission(self, name: str, description: Optional[str] = None, category: str = "general") -> Permission:
        """Create a new permission."""
        try:
            permission = Permission(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                category=category,
                created_at=datetime.utcnow()
            )

            self.db.add(permission)
            self.db.commit()
            self.db.refresh(permission)

            logger.info("Permission created", {"permission_id": permission.id, "name": name})

            return permission

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create permission", {"name": name, "error": str(e)})
            raise

    async def get_all_roles(self) -> List[Role]:
        """Get all roles with their permissions."""
        try:
            roles = self.db.query(Role).options(
                joinedload(Role.permissions)
            ).all()

            return roles

        except Exception as e:
            logger.error("Failed to get all roles", {"error": str(e)})
            raise

    async def get_all_permissions(self) -> List[Permission]:
        """Get all permissions."""
        try:
            permissions = self.db.query(Permission).all()
            return permissions

        except Exception as e:
            logger.error("Failed to get all permissions", {"error": str(e)})
            raise