"""
Database configuration and session management (Phase 6).

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI endpoints.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

from .db_models import Base

logger = logging.getLogger(__name__)

# Database URL from environment
# Format: postgresql://user:password@host:port/database
# Fallback to SQLite for development if PostgreSQL not available
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./syncboard.db"  # Fallback for local development
)

# Convert postgres:// to postgresql:// (Heroku compatibility)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

logger.info(f"Database URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

# Create engine with connection pooling
if DATABASE_URL.startswith("postgresql://"):
    # PostgreSQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,  # Max 5 connections in pool
        max_overflow=10,  # Allow 10 additional connections when pool full
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL query logging
    )
else:
    # SQLite (development/testing)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=False,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables.
    Should be called on application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


def get_db() -> Session:
    """
    Dependency for FastAPI endpoints.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session
            pass

    Automatically commits on success, rolls back on exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside FastAPI.

    Usage:
        with get_db_context() as db:
            user = db.query(DBUser).filter_by(username="alice").first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_health() -> dict:
    """
    Check database connectivity and basic stats.
    Used by health check endpoint.
    """
    try:
        with get_db_context() as db:
            # Simple query to test connectivity
            db.execute("SELECT 1")

            return {
                "database_connected": True,
                "database_type": "postgresql" if DATABASE_URL.startswith("postgresql://") else "sqlite",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "database_connected": False,
            "database_error": str(e),
        }
