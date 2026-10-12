"""
Observability Package for Indian IPO Platform.
Exposes structured JSON logging, correlation context, in-memory metrics,
and diagnostic health check probes.
"""

from ipo_platform.observability.health import (
    HealthAggregator,
    HealthCheckResult,
    HealthStatus,
    SystemHealthReport,
    check_adapters,
    check_database,
    check_notifications,
    check_redis,
)
from ipo_platform.observability.logging import (
    LogContextManager,
    StructuredJSONFormatter,
    clear_context,
    get_correlation_id,
    get_ipo_context,
    log_exception,
    redact_secrets,
    set_correlation_id,
    set_ipo_context,
    setup_logging,
)
from ipo_platform.observability.metrics import (
    Counter,
    Gauge,
    MetricsRegistry,
    Timer,
    default_registry,
)

__all__ = [
    # Logging
    "StructuredJSONFormatter",
    "setup_logging",
    "set_correlation_id",
    "get_correlation_id",
    "set_ipo_context",
    "get_ipo_context",
    "clear_context",
    "LogContextManager",
    "log_exception",
    "redact_secrets",
    # Metrics
    "Counter",
    "Gauge",
    "Timer",
    "MetricsRegistry",
    "default_registry",
    # Health
    "HealthStatus",
    "HealthCheckResult",
    "SystemHealthReport",
    "HealthAggregator",
    "check_database",
    "check_redis",
    "check_adapters",
    "check_notifications",
]
