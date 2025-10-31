"""
Database initialization and session management.

Provides database engine, session factory, and initialization utilities.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from pathlib import Path
import os

from .models import Base

# Database file location
DB_DIR = Path(__file__).parent.parent / 'data'
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / 'production.db'

# Create engine
DATABASE_URL = f'sqlite:///{DB_PATH}'
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={'check_same_thread': False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create scoped session for thread safety
db_session = scoped_session(SessionLocal)


def init_database():
    """
    Initialize database by creating all tables.

    Safe to call multiple times - will only create tables that don't exist.
    """
    print(f"\n{'='*70}")
    print(f"🗄️  DATABASE INITIALIZATION")
    print(f"{'='*70}")
    print(f"Database: {DB_PATH}")
    print(f"Creating tables...")

    # Create all tables
    Base.metadata.create_all(bind=engine)

    print(f"✅ Database initialized successfully")
    print(f"{'='*70}\n")


def get_db():
    """
    Get database session.

    Usage in Flask routes:
        db = get_db()
        try:
            # Use db
            db.commit()
        except:
            db.rollback()
            raise
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_database():
    """
    ⚠️  WARNING: Drops and recreates all tables.

    Use only for development/testing!
    """
    print(f"\n{'='*70}")
    print(f"⚠️  RESETTING DATABASE")
    print(f"{'='*70}")
    print(f"Dropping all tables...")

    Base.metadata.drop_all(bind=engine)

    print(f"Recreating all tables...")
    Base.metadata.create_all(bind=engine)

    print(f"✅ Database reset complete")
    print(f"{'='*70}\n")


# Auto-initialize database on import
if not DB_PATH.exists():
    init_database()
