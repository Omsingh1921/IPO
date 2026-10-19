"""
FastAPI Application Factory & Server Entrypoint for Indian IPO Platform API (Phase 10 - Stage 5).
Initializes OpenAPI documentation, enterprise security middleware, RBAC dependencies,
and global exception handlers with zero-trust production hardening.
"""

from contextlib import asynccontextmanager
import logging
import os
import time
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from ipo_platform.api.exceptions import register_exception_handlers
from ipo_platform.api.routes import api_router
from ipo_platform.observability.metrics import default_registry
from ipo_platform.security.config import SecurityConfig, get_security_config
from ipo_platform.security.middleware import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

logger = logging.getLogger(__name__)

# Metrics instruments
_HTTP_REQUEST_COUNT = default_registry.counter(
    "http_requests_total", "Total count of processed HTTP requests"
)
_HTTP_REQUEST_LATENCY = default_registry.timer(
    "http_request_duration_seconds", "Histogram of HTTP request processing latencies"
)


_scheduler: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and graceful shutdown lifecycles."""
    global _scheduler
    logger.info("Initializing Indian IPO Recommendation Platform API with Production Security...")

    if os.getenv("SCHEDULER_ENABLED", "false").lower() == "true":
        try:
            from ipo_platform.jobs.scheduler import JobScheduler
            from ipo_platform.jobs.daily_briefing_job import run_daily_briefing_job
            from ipo_platform.db.session import get_engine

            _scheduler = JobScheduler()
            engine = get_engine()

            # 1. Daily 12:01 PM Briefing Job
            def _briefing_task() -> None:
                run_daily_briefing_job(engine, notify_channels=["email"])

            _scheduler.schedule_daily_job("daily_briefing", _briefing_task)
            logger.info("Daily briefing scheduler background loop activated.")

            # 2. Automated Recurring Live Market Sync (NSE, BSE, GMP)
            if os.getenv("AUTO_SYNC_ENABLED", "true").lower() in ("true", "1", "yes"):
                from ipo_platform.services.sync_service import SourceSyncService
                sync_interval = float(os.getenv("LIVE_SYNC_INTERVAL_SECONDS", "300.0"))
                sync_service = SourceSyncService(engine)

                def _live_market_sync_task() -> None:
                    try:
                        logger.info("Background auto-sync: Fetching live subscription and quote updates (NSE/BSE/GMP)...")
                        summary = sync_service.sync_all(limit=50, dry_run=False)
                        logger.info(
                            "Background auto-sync complete: %d records ingested/updated, %d GMP quotes recorded.",
                            summary.master_records_ingested,
                            summary.gmp_quotes_recorded,
                        )
                    except Exception as exc:
                        logger.warning("Background live market auto-sync encountered an error: %s", exc)

                _scheduler.schedule_interval_job(
                    "live_market_sync",
                    _live_market_sync_task,
                    interval_seconds=sync_interval,
                    run_immediately=True,
                )
                logger.info("Automated recurring live market sync loop activated (every %.0f seconds).", sync_interval)

            # 3. Market Hours Auto-Scheduler (09:15, 13:00, 17:00 IST cron)
            if os.getenv("MARKET_HOURS_SYNC_ENABLED", "true").lower() in ("true", "1", "yes"):
                scheduled_slots = _scheduler.schedule_market_hours_sync(engine)
                logger.info(
                    "Market Hours Auto-Scheduler activated for IST slots: %s",
                    scheduled_slots,
                )
        except Exception as err:
            logger.warning("Could not initialize scheduler in lifespan: %s", err)

    yield

    if _scheduler:
        try:
            _scheduler.stop_all()
        except Exception as err:
            logger.warning("Error stopping scheduler: %s", err)
    logger.info("Shutting down Indian IPO Recommendation Platform API...")


def create_app(config: Optional[SecurityConfig] = None) -> FastAPI:
    """
    Application factory constructing a hardened, production-grade FastAPI instance.
    Configures security headers, trusted hosts, safe CORS, and rate limiting.
    """
    sec_cfg = config or get_security_config()

    # Configure OpenAPI/Swagger visibility based on environment policy
    docs_url = "/docs" if sec_cfg.docs_enabled else None
    redoc_url = "/redoc" if sec_cfg.docs_enabled else None
    openapi_url = "/openapi.json" if sec_cfg.docs_enabled else None

    app = FastAPI(
        title="Indian IPO Recommendation Platform API",
        description=(
            "Production-Grade REST API platform delivering quantitative IPO intelligence, "
            "multi-factor recommendation scoring (0-100), empirical backtest validation, "
            "diversified portfolio capital allocation, and system observability."
        ),
        version="1.0.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # 1. Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware, config=sec_cfg)

    # 2. Request Payload Size Limiting Middleware
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=sec_cfg.max_request_body_bytes)

    # 3. Production-Safe CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sec_cfg.cors_allowed_origins,
        allow_credentials=sec_cfg.cors_allow_credentials,
        allow_methods=sec_cfg.cors_allowed_methods,
        allow_headers=sec_cfg.cors_allowed_headers,
    )

    # 4. Trusted Host Header Middleware
    if sec_cfg.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=sec_cfg.trusted_hosts,
        )

    # 5. Timing & Telemetry Middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        tags = {
            "method": request.method,
            "path": request.url.path,
            "status_code": str(response.status_code),
        }
        _HTTP_REQUEST_COUNT.inc(1.0, tags=tags)
        _HTTP_REQUEST_LATENCY.observe(duration, tags=tags)

        response.headers["X-Process-Time"] = f"{duration * 1000:.2f}ms"
        return response

    # 6. Global Exception Handlers
    register_exception_handlers(app)

    # 7. Include API Routers
    app.include_router(api_router)

    return app


# Default singleton app instance for ASGI servers (uvicorn, gunicorn)
app = create_app()


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Entrypoint running Uvicorn server."""
    logger.info("Starting Uvicorn server on %s:%s...", host, port)
    uvicorn.run("ipo_platform.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
