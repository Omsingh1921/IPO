"""
Domain Database Exceptions for Indian IPO Platform.
Provides specific exception types for connection failures, constraint violations, and concurrency collisions.
"""


class PlatformDatabaseError(Exception):
    """Base exception for all database operations in the IPO platform."""

    pass


class DatabaseConnectionError(PlatformDatabaseError):
    """Raised when database connection initialization or pooling fails."""

    pass


class DuplicateIPOSlugError(PlatformDatabaseError):
    """Raised on unique constraint violations (e.g. duplicate ipo_id)."""

    pass


class OptimisticLockError(PlatformDatabaseError):
    """Raised when Optimistic Concurrency Control (version_id) detects a write collision."""

    pass


class ConstraintViolationError(PlatformDatabaseError):
    """Raised when foreign key or check constraints are violated."""

    pass


class DataIntegrityError(PlatformDatabaseError):
    """Raised when data mapping or type conversion fails during database persistence."""

    pass
