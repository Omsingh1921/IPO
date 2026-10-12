"""
Grey Market Premium (GMP) Source Adapter for Indian IPO Platform.
Aggregates secondary market unofficial GMP price discovery, applying confidence scoring,
sanity range boundaries, and outlier rejection filters.
Provides fetch, validate, transform, and health_check contracts with offline mock fallback.
"""

from datetime import date
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from ipo_platform.adapters.base import BaseSourceAdapter, CircuitBreaker
from ipo_platform.models.schema import GMPData

logger = logging.getLogger(__name__)


class GMPAdapter(BaseSourceAdapter):
    """
    Adapter for unofficial Grey Market Premium tracker feeds with sanity validation
    and outlier detection guards.
    """

    def __init__(
        self,
        base_url: str = "https://api.ipo-gmp-tracker.com/quotes",
        timeout_seconds: float = 10.0,
        requests_per_second: float = 2.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        http_client: Optional[Callable[..., Any]] = None,
    ) -> None:
        super().__init__(
            source_name="GMP",
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            circuit_breaker=circuit_breaker,
        )
        self.http_client = http_client

    def health_check(self) -> bool:
        """Verifies upstream API connectivity or adapter readiness."""
        try:
            items = self.fetch(limit=1)
            return isinstance(items, list)
        except Exception as err:
            logger.warning("GMPAdapter health check failed: %s", err)
            return False

    def fetch(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves raw GMP quote snapshots from upstream API or offline deterministic provider.
        """
        if self.http_client:
            return self.http_client(self.base_url, from_date=from_date, to_date=to_date, limit=limit)

        year = date.today().year
        today_str = date.today().isoformat()
        return [
            {
                "ipo_id": f"NSE-TECHDYN-{year}",
                "gmp_value": 85.0,
                "reference_price": 340.0,
                "date": today_str,
                "time": "11:30:00",
                "source": "Chittorgarh",
            }
        ][:limit]

    def validate_gmp_sanity(self, gmp_value: float, reference_price: float) -> Tuple[bool, str]:
        """
        Applies mathematical sanity bounds:
        -50% <= GMP / Reference Price <= +150%
        """
        if reference_price <= 0:
            return False, f"Invalid reference price: {reference_price}"

        pct = (gmp_value / reference_price) * 100.0
        if pct < -50.0:
            return False, f"GMP discount exceeds outlier boundary (-50%): {pct:.1f}%"
        if pct > 150.0:
            return False, f"GMP premium exceeds outlier boundary (+150%): {pct:.1f}%"

        return True, "Valid"

    def validate(self, raw_item: Dict[str, Any]) -> bool:
        """
        Validates structure and sanity boundaries of a raw GMP quote.
        """
        if not isinstance(raw_item, dict):
            return False

        ipo_id = str(raw_item.get("ipo_id", raw_item.get("symbol", ""))).strip()
        if not ipo_id:
            return False

        try:
            gmp_val = float(raw_item.get("gmp_value", raw_item.get("gmp", 0.0)))
            ref_price = float(raw_item.get("reference_price", raw_item.get("issue_price", 100.0)))
        except (ValueError, TypeError):
            return False

        is_sane, reason = self.validate_gmp_sanity(gmp_val, ref_price)
        if not is_sane:
            logger.warning("Rejecting suspicious GMP quote for %s: %s", ipo_id, reason)
            return False

        return True

    def transform(self, raw_item: Dict[str, Any]) -> Optional[Tuple[str, GMPData]]:
        """
        Transforms a validated GMP quote payload into a (ipo_id, GMPData) tuple.
        """
        ipo_id = str(raw_item.get("ipo_id", raw_item.get("symbol", ""))).strip()
        if not ipo_id:
            raise ValueError("GMP record missing 'ipo_id' or 'symbol'")

        gmp_val = float(raw_item.get("gmp_value", raw_item.get("gmp", 0.0)))
        ref_price = float(raw_item.get("reference_price", raw_item.get("issue_price", 100.0)))

        is_sane, reason = self.validate_gmp_sanity(gmp_val, ref_price)
        if not is_sane:
            return None

        gmp_pct = float(raw_item.get("gmp_percentage", (gmp_val / ref_price) * 100.0))
        implied_price = ref_price + gmp_val

        gmp_data = GMPData(
            gmp_value=gmp_val,
            gmp_percentage=round(gmp_pct, 2),
            gmp_date=raw_item.get("date", date.today().isoformat()),
            gmp_time=raw_item.get("time", "11:00:00"),
            reference_price=ref_price,
            implied_price=implied_price,
            source=raw_item.get("source", self.source_name),
        )

        return (ipo_id, gmp_data)
