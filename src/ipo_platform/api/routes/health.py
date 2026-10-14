"""
Health Check API Endpoint (Phase 10 - Stage 5).
Exposes GET /health providing real-time system and subsystem health status.
Public endpoint for infrastructure liveness/readiness probes, protected by rate limiting.
"""

from fastapi import APIRouter, Depends, status

from ipo_platform.api.dependencies import get_health_aggregator
from ipo_platform.api.schemas import (
    HealthCheckDetail,
    HealthResponse,
    HealthStatusEnum,
)
from ipo_platform.observability.health import HealthAggregator
from ipo_platform.security.rate_limiter import rate_limit

router = APIRouter(prefix="", tags=["Health"])


def _sanitize_health_message(msg: str) -> str:
    """Removes sensitive credentials, connection URLs, or internal paths from health messages."""
    import re
    if not msg:
        return ""
    # Strip database connection strings with passwords: scheme://user:pass@host:port/db
    sanitized = re.sub(r"[a-zA-Z0-9_+]+://[^:@\s]+:[^@\s]+@[^\s/]+(?::\d+)?/[^\s]*", "<redacted_database_url>", msg)
    # Strip any remaining scheme://host strings
    sanitized = re.sub(r"[a-zA-Z0-9_+]+://[^\s]+", "<redacted_url>", sanitized)
    return sanitized


def _sanitize_health_details(details: dict) -> dict:
    """Removes sensitive keys or values from health details dictionary."""
    sanitized = {}
    for k, v in details.items():
        if k.lower() in ("password", "secret", "url", "dsn", "connection_string", "uri"):
            continue
        if isinstance(v, str):
            sanitized[k] = _sanitize_health_message(v)
        else:
            sanitized[k] = v
    return sanitized


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System & Subsystems Health Check",
    description="Executes diagnostic health probes across database, memory, disk, and subsystems. Public for infrastructure.",
    dependencies=[Depends(rate_limit(endpoint_tag="/health"))],
)
def get_health(
    aggregator: HealthAggregator = Depends(get_health_aggregator),
) -> HealthResponse:
    """Executes all registered health probes and returns consolidated operational status."""
    report = aggregator.run_checks()

    checks_dict = {}
    for name, result in report.checks.items():
        checks_dict[name] = HealthCheckDetail(
            status=HealthStatusEnum(result.status.value),
            message=_sanitize_health_message(result.message),
            duration_ms=result.duration_ms,
            details=_sanitize_health_details(result.details or {}),
        )

    return HealthResponse(
        status=HealthStatusEnum(report.overall_status.value),
        healthy_count=report.healthy_count,
        degraded_count=report.degraded_count,
        unhealthy_count=report.unhealthy_count,
        total_duration_ms=report.total_duration_ms,
        timestamp=report.timestamp,
        checks=checks_dict,
    )
