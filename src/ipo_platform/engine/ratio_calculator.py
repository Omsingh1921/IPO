"""
Financial ratio computation engine for Indian IPO Research Platform.
Provides deterministic formulas for growth rates, margins, valuation multiples, and relative spreads.
"""

from typing import Dict, List, Optional, Union


class RatioCalculator:
    """Deterministic computational engine for financial and valuation metrics."""

    @staticmethod
    def calculate_yoy_growth(
        prev_value: Optional[float], current_value: Optional[float]
    ) -> Optional[float]:
        """Calculates YoY percentage growth: ((current - prev) / prev) * 100."""
        if prev_value is None or current_value is None or prev_value == 0:
            return None
        return round(((current_value - prev_value) / abs(prev_value)) * 100.0, 2)

    @staticmethod
    def calculate_cagr(
        start_val: float, end_val: float, periods: int
    ) -> Optional[float]:
        """Calculates Compound Annual Growth Rate (CAGR) percentage."""
        if start_val <= 0 or end_val <= 0 or periods <= 0:
            return None
        cagr = ((end_val / start_val) ** (1.0 / periods) - 1.0) * 100.0
        return round(cagr, 2)

    @staticmethod
    def calculate_ebitda_margin(
        ebitda: Optional[float], revenue: Optional[float]
    ) -> Optional[float]:
        """Calculates EBITDA Margin: (EBITDA / Revenue) * 100."""
        if ebitda is None or revenue is None or revenue == 0:
            return None
        return round((ebitda / revenue) * 100.0, 2)

    @staticmethod
    def calculate_pat_margin(
        pat: Optional[float], revenue: Optional[float]
    ) -> Optional[float]:
        """Calculates PAT Margin: (PAT / Revenue) * 100."""
        if pat is None or revenue is None or revenue == 0:
            return None
        return round((pat / revenue) * 100.0, 2)

    @staticmethod
    def calculate_pe(
        price: Optional[float], eps: Optional[float]
    ) -> Optional[float]:
        """Calculates Price-to-Earnings (P/E) multiple."""
        if price is None or eps is None or eps <= 0:
            return None
        return round(price / eps, 2)

    @staticmethod
    def calculate_pb(
        price: Optional[float], book_value_per_share: Optional[float]
    ) -> Optional[float]:
        """Calculates Price-to-Book (P/B) multiple."""
        if price is None or book_value_per_share is None or book_value_per_share <= 0:
            return None
        return round(price / book_value_per_share, 2)

    @staticmethod
    def calculate_valuation_spread(
        issue_pe: float, peer_median_pe: float
    ) -> Optional[float]:
        """Calculates valuation premium/discount relative to peer median P/E (%):

        ((issue_pe - peer_median_pe) / peer_median_pe) * 100
        """
        if peer_median_pe <= 0:
            return None
        spread = ((issue_pe - peer_median_pe) / peer_median_pe) * 100.0
        return round(spread, 2)

    @staticmethod
    def calculate_roe(
        pat: Optional[float], net_worth: Optional[float]
    ) -> Optional[float]:
        """Calculates Return on Equity (ROE): (PAT / Net Worth) * 100."""
        if pat is None or net_worth is None or net_worth == 0:
            return None
        return round((pat / net_worth) * 100.0, 2)

    @staticmethod
    def calculate_roce(
        ebit: Optional[float], capital_employed: Optional[float]
    ) -> Optional[float]:
        """Calculates Return on Capital Employed (ROCE): (EBIT / Capital Employed) * 100."""
        if ebit is None or capital_employed is None or capital_employed == 0:
            return None
        return round((ebit / capital_employed) * 100.0, 2)

    @staticmethod
    def calculate_debt_equity(
        total_debt: Optional[float], net_worth: Optional[float]
    ) -> Optional[float]:
        """Calculates Debt-to-Equity ratio: total_debt / net_worth."""
        if total_debt is None or net_worth is None or net_worth == 0:
            return None
        return round(total_debt / net_worth, 2)

    @staticmethod
    def calculate_free_cash_flow(
        operating_cash_flow: Optional[float], capex: Optional[float]
    ) -> Optional[float]:
        """Calculates Free Cash Flow (FCF): OCF - capex."""
        if operating_cash_flow is None:
            return None
        capex_val = capex if capex is not None else 0.0
        return round(operating_cash_flow - capex_val, 2)
