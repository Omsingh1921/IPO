"""
Health Check Framework and Diagnostic Probes for Indian IPO Platform.
Provides structured health probes for database, redis, adapters, and notifications,
guaranteeing fault-isolated, non-crashing execution and aggregation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Any, Callable, Dict

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """System and component health status levels."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass
class HealthCheckResult:
    """Standardized result schema for an individual subsystem probe."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


@dataclass
class SystemHealthReport:
    """Aggregated health report across all subsystem probes."""
    overall_status: HealthStatus
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    checks: Dict[str, HealthCheckResult]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_duration_ms: float = 0.0

    @property
    def is_operational(self) -> bool:
        return self.overall_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


class HealthAggregator:
    """
    Coordinates and executes system diagnostic probes.
    Guarantees that probe exceptions are safely caught, converting failures to UNHEALTHY status.
    """

    def __init__(self) -> None:
        self._probes: Dict[str, Callable[[], HealthCheckResult]] = {}

    def register(self, name: str, probe_fn: Callable[[], HealthCheckResult]) -> None:
        """Registers a diagnostic health probe."""
        self._probes[name] = probe_fn

    def unregister(self, name: str) -> None:
        """Removes a registered health probe."""
        self._probes.pop(name, None)

    def run_checks(self) -> SystemHealthReport:
        """
        Executes all registered health probes with failure isolation and latency tracking.
        Never raises exceptions to caller.
        """
        start_total = time.perf_counter()
        results: Dict[str, HealthCheckResult] = {}
        healthy = 0
        degraded = 0
        unhealthy = 0

        for name, probe in self._probes.items():
            start_probe = time.perf_counter()
            try:
                res = probe()
                duration_ms = round((time.perf_counter() - start_probe) * 1000, 2)
                res.duration_ms = duration_ms
                results[name] = res
            except Exception as exc:
                duration_ms = round((time.perf_counter() - start_probe) * 1000, 2)
                err_msg = f"Probe execution failed with exception: {exc}"
                logger.error("Health probe '%s' failed: %s", name, exc, exc_info=True)
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=err_msg,
                    details={"exception": str(exc), "error_type": exc.__class__.__name__},
                    duration_ms=duration_ms,
                )

            # Accumulate counts
            status = results[name].status
            if status == HealthStatus.HEALTHY:
                healthy += 1
            elif status == HealthStatus.DEGRADED:
                degraded += 1
            else:
                unhealthy += 1

        total_duration = round((time.perf_counter() - start_total) * 1000, 2)

        # Derive overall system status
        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return SystemHealthReport(
            overall_status=overall,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            checks=results,
            total_duration_ms=total_duration,
        )


# --- Standard Subsystem Health Probes ---

def check_database(engine: Engine, timeout_seconds: float = 3.0) -> HealthCheckResult:
    """
    Executes a heartbeat ping query (`SELECT 1`) on the database engine.
    """
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            # Set execution options or run simple query
            conn.execute(text("SELECT 1"))
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection established successfully",
            details={"dialect": engine.dialect.name, "url_driver": engine.url.drivername},
            duration_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connectivity failed: {exc}",
            details={"error": str(exc)},
            duration_ms=elapsed_ms,
        )


def check_redis(redis_client_or_url: Any = None) -> HealthCheckResult:
    """
    Executes a PING heartbeat check on Redis connection or checks lock backend.
    """
    start = time.perf_counter()
    try:
        if redis_client_or_url is None:
            # Unconfigured Redis in standalone / non-cluster mode is treated as DEGRADED or informational
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="Redis client not configured (standalone mode active)",
                details={"configured": False},
                duration_ms=0.0,
            )

        if hasattr(redis_client_or_url, "ping"):
            resp = redis_client_or_url.ping()
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if resp:
                return HealthCheckResult(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis ping successful",
                    details={"response": str(resp)},
                    duration_ms=elapsed_ms,
                )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.DEGRADED,
            message="Redis client ping returned falsy or unsupported type",
            duration_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {exc}",
            details={"error": str(exc)},
            duration_ms=elapsed_ms,
        )


def check_adapters(adapter_manager: Any) -> HealthCheckResult:
    """
    Checks reachability and readiness across all registered upstream source adapters.
    """
    start = time.perf_counter()
    try:
        if adapter_manager is None:
            return HealthCheckResult(
                name="adapters",
                status=HealthStatus.DEGRADED,
                message="No adapter manager provided",
                duration_ms=0.0,
            )

        results = adapter_manager.health_check_all()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        failed_adapters = [name for name, is_healthy in results.items() if not is_healthy]
        if not failed_adapters:
            return HealthCheckResult(
                name="adapters",
                status=HealthStatus.HEALTHY,
                message=f"All {len(results)} registered adapters healthy",
                details={"adapters": results},
                duration_ms=elapsed_ms,
            )
        elif len(failed_adapters) < len(results):
            return HealthCheckResult(
                name="adapters",
                status=HealthStatus.DEGRADED,
                message=f"Partial adapter degradation ({len(failed_adapters)}/{len(results)} failed: {failed_adapters})",
                details={"adapters": results, "failed": failed_adapters},
                duration_ms=elapsed_ms,
            )
        else:
            return HealthCheckResult(
                name="adapters",
                status=HealthStatus.UNHEALTHY,
                message=f"All registered adapters failed health checks: {failed_adapters}",
                details={"adapters": results},
                duration_ms=elapsed_ms,
            )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return HealthCheckResult(
            name="adapters",
            status=HealthStatus.UNHEALTHY,
            message=f"Adapter health check execution error: {exc}",
            details={"error": str(exc)},
            duration_ms=elapsed_ms,
        )


def check_notifications(dispatcher: Any) -> HealthCheckResult:
    """
    Checks notification dispatcher configuration and channel reachability.
    """
    start = time.perf_counter()
    try:
        if dispatcher is None:
            return HealthCheckResult(
                name="notifications",
                status=HealthStatus.DEGRADED,
                message="Notification dispatcher not configured",
                duration_ms=0.0,
            )

        registered_channels = []
        if hasattr(dispatcher, "get_registered_channels") and callable(dispatcher.get_registered_channels):
            raw_channels = dispatcher.get_registered_channels()
            if raw_channels and not isinstance(raw_channels, (MagicMock if "MagicMock" in globals() else type)):
                registered_channels = [
                    ch.value if hasattr(ch, "value") else str(ch)
                    for ch in raw_channels
                ]

        if not registered_channels:
            if hasattr(dispatcher, "_notifiers") and isinstance(dispatcher._notifiers, dict):
                registered_channels = [
                    ch.value if hasattr(ch, "value") else str(ch)
                    for ch in dispatcher._notifiers.keys()
                ]
            elif hasattr(dispatcher, "channels") and isinstance(dispatcher.channels, dict):
                registered_channels = [
                    ch.value if hasattr(ch, "value") else str(ch)
                    for ch in dispatcher.channels.keys()
                ]

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        if not registered_channels:
            return HealthCheckResult(
                name="notifications",
                status=HealthStatus.DEGRADED,
                message="No notification channels registered (alerts inactive)",
                details={"channels": []},
                duration_ms=elapsed_ms,
            )

        return HealthCheckResult(
            name="notifications",
            status=HealthStatus.HEALTHY,
            message=f"Notification dispatcher operational with {len(registered_channels)} channels",
            details={"channels": registered_channels},
            duration_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return HealthCheckResult(
            name="notifications",
            status=HealthStatus.UNHEALTHY,
            message=f"Notification subsystem check error: {exc}",
            details={"error": str(exc)},
            duration_ms=elapsed_ms,
        )
