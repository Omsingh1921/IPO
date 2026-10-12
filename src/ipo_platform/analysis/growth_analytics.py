"""
Growth Analytics Engine for Phase 3 Analysis Engine.
Computes multi-year YoY growth rates, CAGR, margin trajectories, and return ratios.
"""

from typing import Any, Dict, List, Optional
from ..models.schema import MasterIPORecord, FinancialRecord
from ..engine.ratio_calculator import RatioCalculator


class GrowthAnalytics:
    """Computes growth velocity, CAGR, margin trends, and financial health metrics."""

    @staticmethod
    def _extract_number(val: Any) -> Optional[float]:
        if val is None:
            return None
        if hasattr(val, "value"):
            val = val.value
        if isinstance(val, (int, float)):
            return float(val)
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @classmethod
    def analyze_financials(cls, record: MasterIPORecord) -> Dict[str, Any]:
        """Computes comprehensive growth metrics from longitudinal financial records."""
        fin_records: List[FinancialRecord] = record.financial_data
        if not fin_records:
            return {"periods_count": 0, "annual_periods": []}

        annual_records = [
            f for f in fin_records if f.period_type.value == "FY"
        ]

        computed_financials = []
        for idx, fin in enumerate(fin_records):
            rev = cls._extract_number(fin.revenue)
            ebitda = cls._extract_number(fin.EBITDA)
            pat = cls._extract_number(fin.PAT)
            eps = cls._extract_number(fin.EPS)
            debt = cls._extract_number(fin.total_debt)
            net_worth = cls._extract_number(fin.book_value_per_share)

            # YoY growth calculations
            rev_growth = None
            pat_growth = None
            if idx > 0 and fin_records[idx - 1].period_type == fin.period_type:
                prev_rev = cls._extract_number(fin_records[idx - 1].revenue)
                prev_pat = cls._extract_number(fin_records[idx - 1].PAT)
                rev_growth = RatioCalculator.calculate_yoy_growth(prev_rev, rev)
                pat_growth = RatioCalculator.calculate_yoy_growth(prev_pat, pat)

            ebitda_margin = RatioCalculator.calculate_ebitda_margin(ebitda, rev)
            pat_margin = RatioCalculator.calculate_pat_margin(pat, rev)

            computed_financials.append(
                {
                    "period_name": fin.financial_period,
                    "period_type": fin.period_type.value,
                    "revenue_cr": rev,
                    "revenue_growth_yoy_percent": rev_growth,
                    "ebitda_cr": ebitda,
                    "ebitda_margin_percent": ebitda_margin,
                    "pat_cr": pat,
                    "pat_growth_yoy_percent": pat_growth,
                    "eps": eps,
                    "debt_cr": debt,
                    "roe_percent": cls._extract_number(fin.ROE),
                    "roce_percent": cls._extract_number(fin.ROCE),
                    "debt_equity": cls._extract_number(fin.debt_equity),
                }
            )

        # CAGR calculation across annual periods
        revenue_cagr = None
        pat_cagr = None
        if len(annual_records) >= 2:
            first_rev = cls._extract_number(annual_records[0].revenue)
            last_rev = cls._extract_number(annual_records[-1].revenue)
            periods = len(annual_records) - 1
            if first_rev and last_rev:
                revenue_cagr = RatioCalculator.calculate_cagr(first_rev, last_rev, periods)

            first_pat = cls._extract_number(annual_records[0].PAT)
            last_pat = cls._extract_number(annual_records[-1].PAT)
            if first_pat and last_pat:
                pat_cagr = RatioCalculator.calculate_cagr(first_pat, last_pat, periods)

        return {
            "periods_count": len(fin_records),
            "financial_periods": computed_financials,
            "revenue_cagr_percent": revenue_cagr,
            "pat_cagr_percent": pat_cagr,
        }
