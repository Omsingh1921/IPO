from typing import Dict, List, Optional
from ..models.schema import SubscriptionCategory



class MomentumCalculator:
    """Calculates subscription acceleration and bidding velocity metrics."""

    @staticmethod
    def calculate_category_multiple(shares_bid: int, shares_offered: int) -> float:
        """Calculates subscription multiple: shares_bid / shares_offered."""
        if shares_offered <= 0:
            return 0.0
        return round(shares_bid / shares_offered, 2)

    @staticmethod
    def calculate_bidding_acceleration(
        previous_day_bids: int, current_day_bids: int
    ) -> Optional[float]:
        """Calculates percentage acceleration in bid volume between bidding days.

        ((current_day_bids - previous_day_bids) / previous_day_bids) * 100
        """
        if previous_day_bids <= 0:
            return None
        acceleration = ((current_day_bids - previous_day_bids) / previous_day_bids) * 100.0
        return round(acceleration, 2)

    @staticmethod
    def calculate_institutional_demand_ratio(
        qib_multiple: float, retail_multiple: float
    ) -> Optional[float]:
        """Calculates ratio of QIB institutional demand to retail demand.

        qib_multiple / retail_multiple
        """
        if retail_multiple <= 0:
            return None
        return round(qib_multiple / retail_multiple, 2)

    @staticmethod
    def summarize_subscription(
        subscription_data: Dict[str, SubscriptionCategory],
    ) -> Dict[str, float]:
        """Extracts category-wise subscription multiples from a subscription category dict."""
        summary = {}
        for category_name, sub in subscription_data.items():
            summary[category_name] = sub.subscription_multiple
        return summary

