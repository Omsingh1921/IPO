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


# =========================================================================
# Phase 2: Upstream Feeds Live Latency & Diagnostic Probes
# =========================================================================

import concurrent.futures
from datetime import datetime, timedelta, timezone
import time
import urllib.error
from typing import Optional
from ipo_platform.api.schemas import UpstreamFeedProbeDetail, UpstreamFeedsHealthResponse

IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")
_feeds_cache: Optional[UpstreamFeedsHealthResponse] = None
_feeds_cache_time: float = 0.0
_FEEDS_CACHE_TTL_SECONDS = 12.0


def _probe_single_feed(feed_key: str) -> UpstreamFeedProbeDetail:
    """Probes individual upstream market source and records live network latency."""
    from ipo_platform.adapters.live_market_client import default_live_market_client

    t0 = time.perf_counter()
    now_ist = datetime.now(IST_TIMEZONE)
    ts_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    client = default_live_market_client
    name_map = {"bse": "BSE India", "nse": "NSE India", "gmp": "InvestorGain GMP"}

    try:
        if feed_key == "bse":
            items = client.fetch_bse_live(limit=1)
            name = name_map["bse"]
        elif feed_key == "nse":
            items = client.fetch_nse_live(limit=1)
            name = name_map["nse"]
        elif feed_key == "gmp":
            items = client.fetch_gmp_live(limit=1)
            name = name_map["gmp"]
        else:
            raise ValueError(f"Unknown feed key: {feed_key}")

        latency = round((time.perf_counter() - t0) * 1000, 1)
        return UpstreamFeedProbeDetail(
            name=name,
            status="healthy",
            latency_ms=latency,
            http_code=200,
            items_count=len(items),
            last_check=ts_str,
            error=None,
        )
    except urllib.error.HTTPError as he:
        latency = round((time.perf_counter() - t0) * 1000, 1)
        return UpstreamFeedProbeDetail(
            name=name_map.get(feed_key, feed_key.upper()),
            status="unhealthy",
            latency_ms=latency,
            http_code=he.code,
            items_count=0,
            last_check=ts_str,
            error=f"HTTP {he.code}: {he.reason}",
        )
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000, 1)
        http_code = getattr(exc, "code", None)
        return UpstreamFeedProbeDetail(
            name=name_map.get(feed_key, feed_key.upper()),
            status="unhealthy",
            latency_ms=latency,
            http_code=http_code,
            items_count=0,
            last_check=ts_str,
            error=str(exc)[:500],
        )


@router.get(
    "/health/feeds",
    response_model=UpstreamFeedsHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Upstream Market Feeds Latency & Live Health Probes",
    description="Probes live connectivity and measures end-to-end network latency (ms) for BSE, NSE, and InvestorGain GMP feeds concurrently.",
    dependencies=[Depends(rate_limit(endpoint_tag="/health/feeds"))],
)
def get_feeds_health(force_refresh: bool = False) -> UpstreamFeedsHealthResponse:
    """Executes concurrent diagnostic probes against BSE, NSE, and GMP upstream feeds."""
    global _feeds_cache, _feeds_cache_time
    now_perf = time.perf_counter()
    if not force_refresh and _feeds_cache is not None and (now_perf - _feeds_cache_time) < _FEEDS_CACHE_TTL_SECONDS:
        return _feeds_cache

    t_start = time.perf_counter()
    feeds_res = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {k: pool.submit(_probe_single_feed, k) for k in ("bse", "nse", "gmp")}
        for k, fut in futures.items():
            feeds_res[k] = fut.result()

    total_duration = round((time.perf_counter() - t_start) * 1000, 1)
    unhealthy_count = sum(1 for f in feeds_res.values() if f.status != "healthy")

    if unhealthy_count == 0:
        overall = "healthy"
    elif unhealthy_count < len(feeds_res):
        overall = "degraded"
    else:
        overall = "unhealthy"

    now_utc = datetime.now(timezone.utc).isoformat()
    response = UpstreamFeedsHealthResponse(
        overall_status=overall,
        timestamp=now_utc,
        total_probe_duration_ms=total_duration,
        feeds=feeds_res,
    )
    _feeds_cache = response
    _feeds_cache_time = now_perf
    return response

