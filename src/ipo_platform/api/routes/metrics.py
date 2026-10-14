"""
Observability Metrics Route Handlers (Phase 10 - Stage 5).
Exposes GET /metrics delivering an in-memory snapshot of platform counters, gauges, and timers.
Restricted to ADMIN role. Protected by rate limiting.
"""

from fastapi import APIRouter, Depends, status

from ipo_platform.api.dependencies import get_metrics_registry
from ipo_platform.api.schemas import MetricsResponse
from ipo_platform.observability.metrics import MetricsRegistry
from ipo_platform.security.rate_limiter import rate_limit
from ipo_platform.security.rbac import Role, require_role

router = APIRouter(prefix="", tags=["Observability"])


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Platform Telemetry Metrics Snapshot",
    description="Returns current snapshot of platform counters, gauges, and request execution timers. Requires ADMIN role.",
    dependencies=[Depends(require_role(Role.ADMIN)), Depends(rate_limit(endpoint_tag="/metrics"))],
)
def get_metrics(
    registry: MetricsRegistry = Depends(get_metrics_registry),
) -> MetricsResponse:
    """Delivers instantaneous metrics snapshot."""
    snapshot = registry.snapshot()
    return MetricsResponse(
        timestamp=snapshot.get("timestamp", 0.0),
        counters=snapshot.get("counters", []),
        gauges=snapshot.get("gauges", []),
        timers=snapshot.get("timers", []),
    )
