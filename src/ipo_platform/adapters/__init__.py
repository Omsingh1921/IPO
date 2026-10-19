"""
Source Adapters Package for Indian IPO Platform.
Exposes base adapter contracts, resiliency primitives, adapter manager,
and implementations for NSE, BSE, and GMP feeds.
"""

from ipo_platform.adapters.adapter_manager import AdapterManager, SourceSyncSummary
from ipo_platform.adapters.base import (
    AdapterSyncResult,
    BaseSourceAdapter,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    TokenBucketRateLimiter,
)
from ipo_platform.adapters.bse_adapter import BSEAdapter
from ipo_platform.adapters.financials_adapter import FinancialsBridgeAdapter
from ipo_platform.adapters.gmp_adapter import GMPAdapter
from ipo_platform.adapters.live_market_client import LiveMarketClient, default_live_market_client
from ipo_platform.adapters.nse_adapter import NSEAdapter

__all__ = [
    "AdapterManager",
    "SourceSyncSummary",
    "BaseSourceAdapter",
    "AdapterSyncResult",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitBreakerState",
    "TokenBucketRateLimiter",
    "NSEAdapter",
    "BSEAdapter",
    "GMPAdapter",
    "FinancialsBridgeAdapter",
    "LiveMarketClient",
    "default_live_market_client",
]
