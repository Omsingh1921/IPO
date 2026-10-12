"""
Declarative Base for SQLAlchemy 2.0 ORM Models.
Initializes common base class for database entity mappings.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root Declarative Base for all SQLAlchemy 2.0 ORM models in IPO platform."""

    pass
