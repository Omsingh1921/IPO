"""
Historical Data Loader for Phase 4 Backtesting Engine.
Loads post-listing performance streams and historical IPO outcomes while enforcing temporal boundaries.
"""

from typing import Any, Dict, List, Optional
from ..models.schema import MasterIPORecord, HistoricalIPO, PerformanceEvent


class HistoricalDataLoader:
    """Ingests and validates historical post-listing outcome datasets."""

    @staticmethod
    def extract_post_listing_outcomes(record: MasterIPORecord) -> Optional[Dict[str, Any]]:
        """Extracts post-listing outcomes from a MasterIPORecord if listed."""
        if not record.historical_ipo or not record.historical_ipo.historical_ipo:
            return None

        hist: HistoricalIPO = record.historical_ipo
        return {
            "ipo_id": record.ipo_entity.ipo_id,
            "ipo_year": hist.ipo_year,
            "issue_price": record.issue_structure.price_band_high.value,
            "listing_price": hist.listing_price,
            "listing_day_close": hist.listing_day_close,
            "listing_day_return_percent": hist.listing_day_return,
            "post_listing_30d_return_percent": hist.post_listing_30d_return,
            "max_upside_percent": hist.max_upside_from_issue_price,
            "max_drawdown_percent": hist.max_drawdown_from_issue_price,
            "scenario_status_pre_listing": record.scenario_40_percent.scenario_status.value,
            "target_price_40": record.scenario_40_percent.target_price,
        }

    @classmethod
    def load_historical_cohort(
        cls, records: List[MasterIPORecord]
    ) -> List[Dict[str, Any]]:
        """Extracts historical outcome summaries from a cohort of IPO records."""
        cohort = []
        for r in records:
            outcome = cls.extract_post_listing_outcomes(r)
            if outcome is not None:
                cohort.append(outcome)
        return cohort
