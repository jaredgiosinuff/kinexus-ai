"""
Database connection management for Kinexus AI.

Provides SQLAlchemy engine creation, session management, and connection pooling
with proper configuration for production environments.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration with environment-based settings."""

    def __init__(self):
        self.database_url = self._build_database_url()
        self.echo = os.getenv("SQL_ECHO", "false").lower() == "true"
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    def _build_database_url(self) -> str:
        """Build database URL from environment variables."""
        # For local development, allow simple DATABASE_URL override
        if database_url := os.getenv("DATABASE_URL"):
            return database_url

        # Build from components for production
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "kinexusai")
        username = os.getenv("DB_USER", "kinexus")
        password = os.getenv("DB_PASSWORD", "")

        if not password:
            # For Alembic offline mode or development without actual DB
            return f"postgresql://{username}:placeholder@{host}:{port}/{database}"

        return f"postgresql://{username}:{password}@{host}:{port}/{database}"


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = create_engine(
                self.config.database_url,
                echo=self.config.echo,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True,  # Validate connections before use
            )
            logger.info("Database engine created")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    def drop_tables(self):
        """Drop all tables in the database. Use with caution!"""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.

        Usage:
            with db_manager.get_session() as session:
                user = session.query(User).first()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self):
        """Close the database engine and all connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for dependency injection
def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency for getting database sessions."""
    with db_manager.get_session() as session:
        yield session


def init_database():
    """Initialize database tables. Call this on application startup."""
    db_manager.create_tables()


def close_database():
    """Close database connections. Call this on application shutdown."""
    db_manager.close()


# Database URL for Alembic
def get_alembic_database_url() -> str:
    """Get database URL for Alembic migrations."""
    config = DatabaseConfig()
    return config.database_url
