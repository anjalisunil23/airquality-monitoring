"""
Database connection and session management for Smart Classroom Monitoring.
Supports PostgreSQL (for production/Docker) with graceful fallback to SQLite for local development.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from app.config import DATABASE_URL

logger = logging.getLogger("uvicorn.error")

Base = declarative_base()

def init_engine_and_session():
    """
    Initializes database engine. First attempts PostgreSQL via DATABASE_URL.
    If PostgreSQL is unreachable, falls back seamlessly to SQLite.
    """
    target_url = DATABASE_URL
    is_sqlite = False

    try:
        if "postgresql" in target_url:
            # If database does not exist, try creating it via default maintenance db
            try:
                test_engine = create_engine(
                    target_url,
                    connect_args={"connect_timeout": 3},
                    pool_pre_ping=True
                )
                with test_engine.connect() as conn:
                    logger.info(f"Connected successfully to PostgreSQL database: {target_url.split('@')[-1]}")
                engine = test_engine
            except Exception as conn_err:
                if 'does not exist' in str(conn_err):
                    logger.info("Target PostgreSQL database does not exist. Attempting automatic creation...")
                    try:
                        import psycopg
                        # Connect to maintenance db 'postgres'
                        base_url = target_url.rsplit('/', 1)[0] + '/postgres'
                        db_name = target_url.rsplit('/', 1)[1]
                        with psycopg.connect(base_url, autocommit=True) as p_conn:
                            with p_conn.cursor() as cur:
                                cur.execute(f'CREATE DATABASE "{db_name}"')
                        logger.info(f"Created database '{db_name}' successfully on PostgreSQL.")
                        test_engine = create_engine(target_url, pool_pre_ping=True)
                        engine = test_engine
                    except Exception as create_err:
                        raise create_err
                else:
                    raise conn_err
        else:
            engine = create_engine(target_url, connect_args={"check_same_thread": False})
            is_sqlite = True
    except Exception as e:
        logger.warning(
            f"Could not connect to PostgreSQL ({e}). Falling back to local SQLite database: classroom.db"
        )
        target_url = "sqlite:///./classroom.db"
        engine = create_engine(target_url, connect_args={"check_same_thread": False})
        is_sqlite = True

    session_maker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, session_maker, target_url, is_sqlite


engine, SessionLocal, ACTIVE_DB_URL, IS_SQLITE = init_engine_and_session()


def get_db():
    """FastAPI Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined in Base models"""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")
