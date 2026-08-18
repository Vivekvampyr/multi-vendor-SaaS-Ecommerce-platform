import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy 2.0 Engine Configuration
# pool_pre_ping verifies connections are alive before handing them to requests
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    echo=False,  # Set to True for verbose SQL query debugging
)

# Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Declarative Base
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Closes the session after the request finishes.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> dict:
    """
    Utility to verify database connectivity.
    Returns status dict with connectivity info.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"connected": True, "message": "Database connection successful"}
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", str(exc))
        return {
            "connected": False,
            "message": f"Database connection unavailable: {str(exc)}",
        }
