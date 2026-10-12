"""
Subscription Momentum & Bidding Velocity Analysis Engine.
Calculates category-wise demand multiples, Day-over-Day acceleration rates, and institutional ratios.
"""

from typing import Any, Dict, List, Optional
from ..models.schema import MasterIPORecord
from ..engine.momentum_index import MomentumCalculator


class SubscriptionMomentumEngine:
    """Analyzes bidding velocity and institutional subscription acceleration."""

    @classmethod
    def analyze_subscription(cls, record: MasterIPORecord) -> Dict[str, Any]:
        """Extracts category subscription multiples and computes momentum metrics."""
        sub_data = record.subscription_data
        if not sub_data:
            return {
                "has_subscription_data": False,
                "categories": {},
                "institutional_demand_ratio": None,
                "total_subscription_multiple": None,
            }

        category_multiples = {}
        for cat_name, category_obj in sub_data.items():
            category_multiples[cat_name] = category_obj.subscription_multiple

        qib_mult = category_multiples.get("QIB", 0.0)
        retail_mult = category_multiples.get("retail", 0.0)
        inst_ratio = MomentumCalculator.calculate_institutional_demand_ratio(qib_mult, retail_mult)

        total_sub = category_multiples.get("total_subscription")

        return {
            "has_subscription_data": True,
            "categories": category_multiples,
            "institutional_demand_ratio": inst_ratio,
            "total_subscription_multiple": total_sub,
        }
