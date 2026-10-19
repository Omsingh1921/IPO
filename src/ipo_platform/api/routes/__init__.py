"""
Route Registry for Indian IPO Recommendation Platform API.
Aggregates all domain routers: health, ipos, recommendation, portfolio, and metrics.
"""

from fastapi import APIRouter

from ipo_platform.api.routes.auth import router as auth_router
from ipo_platform.api.routes.dashboard import router as dashboard_router
from ipo_platform.api.routes.health import router as health_router
from ipo_platform.api.routes.ipos import router as ipos_router
from ipo_platform.api.routes.metrics import router as metrics_router
from ipo_platform.api.routes.portfolio import router as portfolio_router
from ipo_platform.api.routes.recommendation import router as recommendation_router
from ipo_platform.api.routes.scheduler import router as scheduler_router
from ipo_platform.api.routes.wishlist import router as wishlist_router

api_router = APIRouter()

# Register all modular sub-routers
api_router.include_router(dashboard_router)
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(ipos_router)
api_router.include_router(recommendation_router)
api_router.include_router(portfolio_router)
api_router.include_router(metrics_router)
api_router.include_router(wishlist_router)
api_router.include_router(scheduler_router)

__all__ = [
    "api_router",
    "auth_router",
    "dashboard_router",
    "health_router",
    "ipos_router",
    "recommendation_router",
    "portfolio_router",
    "metrics_router",
    "wishlist_router",
    "scheduler_router",
]

