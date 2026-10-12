"""
Database Session Management and Engine Factory for Indian IPO Platform.
Provides SQLAlchemy 2.0 engine creation, connection pooling, and session lifecycle management.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ipo_platform.db.base import Base
from ipo_platform.db.exceptions import DatabaseConnectionError

DEFAULT_DATABASE_URL = "sqlite:///:memory:"


def get_engine(db_url: Optional[str] = None, echo: bool = False) -> Engine:
    """
    Creates and returns a SQLAlchemy Engine instance with connection pooling.

    Args:
        db_url: Database connection string. If None, checks `DATABASE_URL` env var
                or defaults to SQLite in-memory.
        echo: If True, log SQL queries to stderr.

    Returns:
        SQLAlchemy Engine instance.
    """
    url = db_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    try:
        if url.startswith("sqlite"):
            if ":memory:" in url:
                engine = create_engine(
                    url,
                    echo=echo,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )
            else:
                engine = create_engine(
                    url,
                    echo=echo,
                    connect_args={"check_same_thread": False},
                )
        else:
            engine = create_engine(
                url,
                echo=echo,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,
                pool_pre_ping=True,
            )
        return engine
    except Exception as err:
        raise DatabaseConnectionError(f"Failed to create database engine for '{url}': {err}") from err


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """
    Creates a configured sessionmaker instance bound to the provided engine.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        Configured sessionmaker bound to engine.
    """
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@contextmanager
def get_db_session(session_factory_or_engine) -> Generator[Session, None, None]:
    """
    Context manager for database session lifecycle with automatic commit and rollback.

    Args:
        session_factory_or_engine: A sessionmaker instance or Engine instance.

    Yields:
        Active SQLAlchemy Session instance.
    """
    if isinstance(session_factory_or_engine, Engine):
        factory = get_session_factory(session_factory_or_engine)
    else:
        factory = session_factory_or_engine

    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine) -> None:
    """
    Initializes database tables according to ORM metadata.

    Args:
        engine: SQLAlchemy Engine instance.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as err:
        raise DatabaseConnectionError(f"Failed to initialize database tables: {err}") from err
