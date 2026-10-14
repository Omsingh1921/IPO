"""
API Package for Indian IPO Recommendation Platform (Phase 10 - Stage 4).
Exposes FastAPI application factory, ASGI app instance, and submodules.
"""

from ipo_platform.api.app import app, create_app, run_server

__all__ = ["create_app", "app", "run_server"]
