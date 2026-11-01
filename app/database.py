
"""
Database connection and session management for Smart Classroom Monitoring.

Supports:
- PostgreSQL for Render production deployment.
- SQLite for local development fallback.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL


logger = logging.getLogger("uvicorn.error")

Base = declarative_base()


def init_engine_and_session():
    """
    Initialize the database engine.

    First attempts PostgreSQL using DATABASE_URL.
    Falls back to SQLite if PostgreSQL is unavailable.
    """

    target_url = DATABASE_URL
    is_sqlite = False

    try:
        # Check whether the URL is PostgreSQL.
        if target_url.startswith(("postgres://", "postgresql://")):

            # Convert Render's postgres:// URL to postgresql://
            if target_url.startswith("postgres://"):
                target_url = target_url.replace(
                    "postgres://",
                    "postgresql://",
                    1
                )

            logger.info("Attempting PostgreSQL connection...")

            engine = create_engine(
                target_url,
                connect_args={"connect_timeout": 10},
                pool_pre_ping=True
            )

            # Verify the database connection.
            with engine.connect():
                logger.info("Successfully connected to PostgreSQL.")

        else:
            # Local SQLite database.
            logger.info("Using SQLite database.")

            engine = create_engine(
                target_url,
                connect_args={"check_same_thread": False}
            )

            is_sqlite = True

    except Exception as error:

        logger.exception(
            "PostgreSQL connection failed. "
            "Falling back to SQLite: %s",
            error
        )

        target_url = "sqlite:///./classroom.db"

        engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False}
        )

        is_sqlite = True

    # Create database session factory.
    session_maker = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    return engine, session_maker, target_url, is_sqlite


# Initialize database engine and session.
engine, SessionLocal, ACTIVE_DB_URL, IS_SQLITE = init_engine_and_session()


def get_db():
    """
    FastAPI database dependency.
    Provides a database session for each request.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def init_db():
    """
    Create all database tables defined in models.py.
    """

    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    logger.info(
        "Database tables verified/created successfully."
    )

