"""
Dependency Injection Framework for Indian IPO Platform API (Phase 10 - Stage 4).
Provides modular, overridable FastAPI dependencies for engines, repositories, and services.
"""

from typing import Generator, Optional
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from ipo_platform.db.session import get_db_session, get_engine
from ipo_platform.observability.health import (
    HealthAggregator,
    check_adapters,
    check_database,
    check_notifications,
    check_redis,
)
from ipo_platform.observability.metrics import MetricsRegistry, default_registry
from ipo_platform.portfolio.portfolio_engine import IPOPortfolioEngine
from ipo_platform.recommendation.recommendation_engine import IPORecommendationEngine
from ipo_platform.recommendation.validation import RecommendationValidationEngine
from ipo_platform.services.query_service import IPOQueryService

# Module-level singletons for stateless engine instances
_DB_ENGINE: Optional[Engine] = None
_RECOMMENDATION_ENGINE: Optional[IPORecommendationEngine] = None
_VALIDATION_ENGINE: Optional[RecommendationValidationEngine] = None
_PORTFOLIO_ENGINE: Optional[IPOPortfolioEngine] = None


def get_db_engine() -> Engine:
    """Returns or creates the platform SQLAlchemy engine singleton."""
    global _DB_ENGINE
    if _DB_ENGINE is None:
        _DB_ENGINE = get_engine()
    return _DB_ENGINE


def set_db_engine(engine: Optional[Engine]) -> None:
    """Configures or resets the database engine singleton (useful in tests)."""
    global _DB_ENGINE
    _DB_ENGINE = engine


def get_db() -> Generator[Session, None, None]:
    """
    Yields an active database session with automatic transaction management.
    """
    engine = get_db_engine()
    with get_db_session(engine) as session:
        yield session


def get_query_service() -> IPOQueryService:
    """
    Dependency returning an IPOQueryService instance initialized with the DB engine.
    """
    return IPOQueryService(engine=get_db_engine())


def get_recommendation_engine() -> IPORecommendationEngine:
    """
    Dependency returning the IPORecommendationEngine singleton.
    """
    global _RECOMMENDATION_ENGINE
    if _RECOMMENDATION_ENGINE is None:
        _RECOMMENDATION_ENGINE = IPORecommendationEngine()
    return _RECOMMENDATION_ENGINE


def get_validation_engine() -> RecommendationValidationEngine:
    """
    Dependency returning the RecommendationValidationEngine singleton.
    """
    global _VALIDATION_ENGINE
    if _VALIDATION_ENGINE is None:
        rec_engine = get_recommendation_engine()
        _VALIDATION_ENGINE = RecommendationValidationEngine(engine=rec_engine)
    return _VALIDATION_ENGINE


def get_portfolio_engine() -> IPOPortfolioEngine:
    """
    Dependency returning the IPOPortfolioEngine singleton.
    """
    global _PORTFOLIO_ENGINE
    if _PORTFOLIO_ENGINE is None:
        _PORTFOLIO_ENGINE = IPOPortfolioEngine()
    return _PORTFOLIO_ENGINE


def get_health_aggregator() -> HealthAggregator:
    """
    Builds and returns a HealthAggregator configured with standard subsystem probes.
    """
    aggregator = HealthAggregator()
    engine = get_db_engine()

    # Register standard diagnostic probes
    aggregator.register("database", lambda: check_database(engine))
    aggregator.register("redis", lambda: check_redis(None))
    aggregator.register("notifications", lambda: check_notifications(None))

    return aggregator


def get_metrics_registry() -> MetricsRegistry:
    """
    Dependency returning the active platform MetricsRegistry.
    """
    return default_registry
