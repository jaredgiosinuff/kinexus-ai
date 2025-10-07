#!/usr/bin/env python3
"""
Database setup script for Kinexus AI development.

This script creates the database tables using SQLAlchemy directly,
which is useful for development without requiring a full PostgreSQL setup.

For production, use Alembic migrations instead.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.connection import init_database, close_database
from database.models import Base, User, UserRole
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_dev_database():
    """Set up database for development."""
    try:
        # Set default environment variables for development
        os.environ.setdefault("DB_HOST", "localhost")
        os.environ.setdefault("DB_PORT", "5432")
        os.environ.setdefault("DB_NAME", "kinexusai_dev")
        os.environ.setdefault("DB_USER", "kinexus")
        os.environ.setdefault("DB_PASSWORD", "devpassword")

        logger.info("Creating database tables...")
        init_database()
        logger.info("Database tables created successfully!")

        # Optionally create a default admin user
        create_default_admin = input("Create default admin user? (y/N): ").lower() == 'y'
        if create_default_admin:
            create_admin_user()

    except Exception as e:
        logger.error(f"Failed to set up database: {e}")
        sys.exit(1)
    finally:
        close_database()


def create_admin_user():
    """Create a default admin user for development."""
    from database.connection import db_manager
    from passlib.context import CryptContext
    from uuid import uuid4

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    with db_manager.get_session() as session:
        # Check if admin user already exists
        existing_admin = session.query(User).filter_by(email="admin@kinexusai.local").first()
        if existing_admin:
            logger.info("Admin user already exists")
            return

        # Create admin user
        admin_user = User(
            id=uuid4(),
            email="admin@kinexusai.local",
            password_hash=pwd_context.hash("admin123"),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True
        )

        session.add(admin_user)
        session.commit()
        logger.info("Created admin user: admin@kinexusai.local / admin123")


if __name__ == "__main__":
    setup_dev_database()