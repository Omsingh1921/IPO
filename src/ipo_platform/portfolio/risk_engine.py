"""
Portfolio Risk Engine for Indian IPO Capital Allocation (Phase 10 - Stage 3).
Calculates:
- Portfolio Risk Score
- Concentration Risk (Herfindahl-Hirschman Index & Max Position metrics)
- Exposure Risk (Capital-at-Risk)
- Expected Return, Expected Risk, and Sharpe-like Score
- Risk Category assignment (LOW, MEDIUM, HIGH, VERY_HIGH)
"""

import math
from typing import Dict, List, Optional, Tuple

from ipo_platform.portfolio.allocation_models import (
    CapitalAllocation,
    PortfolioRiskCategory,
    RiskProfile,
)
from ipo_platform.recommendation.scoring_models import RecommendationCategory, RiskLevel


class PortfolioRiskEngine:
    """
    Quantitative Risk & Analytics Engine for IPO Portfolio Allocation.
    Computes risk exposure metrics, concentration limits, expected payoff curves,
    and portfolio risk categories.
    """

    @staticmethod
    def estimate_ipo_payoff_profile(
        recommendation: RecommendationCategory,
        composite_score: float,
        risk_level: RiskLevel,
    ) -> Tuple[float, float]:
        """
        Estimates expected listing return (%) and expected volatility/downside risk (%)
        from quantitative recommendation factors.
        """
        if recommendation == RecommendationCategory.STRONG_SUBSCRIBE:
            # Baseline +25% return, with bonus for higher composite score (up to +45%)
            expected_ret = 25.0 + max(0.0, (composite_score - 75.0) / 25.0 * 20.0)
            expected_risk = 10.0 if risk_level == RiskLevel.LOW else 14.0
        elif recommendation == RecommendationCategory.SUBSCRIBE:
            # Baseline +12% return (up to +24%)
            expected_ret = 12.0 + max(0.0, (composite_score - 60.0) / 15.0 * 12.0)
            expected_risk = 15.0 if risk_level == RiskLevel.LOW else 18.0
        elif recommendation == RecommendationCategory.NEUTRAL:
            # Range-bound +2% to +8%
            expected_ret = 2.0 + max(0.0, (composite_score - 45.0) / 15.0 * 6.0)
            expected_risk = 22.0
        else:  # AVOID
            expected_ret = -8.0 - max(0.0, (45.0 - composite_score) / 45.0 * 12.0)
            expected_risk = 35.0

        if risk_level == RiskLevel.VERY_HIGH:
            expected_risk += 10.0
        elif risk_level == RiskLevel.HIGH:
            expected_risk += 5.0

        return round(expected_ret, 2), round(expected_risk, 2)

    @classmethod
    def calculate_portfolio_analytics(
        cls,
        allocations: List[CapitalAllocation],
        total_capital: float,
        total_allocated: float,
        risk_free_rate: float = 6.5,  # Indian 10Y G-Sec benchmark rate ~6.5%
    ) -> Tuple[float, float, float]:
        """
        Calculates:
        1. Expected Return % (weighted average across active positions + cash yield)
        2. Expected Risk % (weighted position volatility adjusted for cash cushion)
        3. Sharpe-like Score: (Expected Return - Risk Free Rate) / Expected Risk
        """
        if total_capital <= 0 or not allocations or total_allocated <= 0:
            return 0.0, 0.0, 0.0

        # Weighted return across positions
        unallocated_cash = max(0.0, total_capital - total_allocated)
        cash_weight = unallocated_cash / total_capital
        cash_return = 4.0  # Liquid fund / savings yield ~4.0%

        invested_return = sum(
            a.expected_return * (a.allocated_amount / total_capital)
            for a in allocations
        )
        total_expected_return = invested_return + (cash_weight * cash_return)

        # Portfolio aggregate volatility / risk
        # Scaled by invested capital proportion (cash dampens portfolio volatility)
        invested_risk = sum(
            a.expected_risk * (a.allocated_amount / total_allocated)
            for a in allocations
        )
        invested_fraction = total_allocated / total_capital
        total_expected_risk = invested_risk * invested_fraction

        # Sharpe-like score
        if total_expected_risk > 0.0:
            excess_return = total_expected_return - risk_free_rate
            sharpe = excess_return / total_expected_risk
        else:
            sharpe = 0.0

        return (
            round(total_expected_return, 2),
            round(total_expected_risk, 2),
            round(sharpe, 2),
        )

    @staticmethod
    def calculate_concentration_risk(
        allocations: List[CapitalAllocation],
        total_allocated: float,
    ) -> float:
        """
        Calculates concentration risk score (0.0 to 100.0) using Herfindahl-Hirschman Index (HHI).
        Normalized HHI: sum(weight_i ^ 2) * 100.
        Single position = 100.0 (maximum concentration).
        Evenly distributed across 5 positions = 20.0.
        """
        if not allocations or total_allocated <= 0:
            return 0.0

        weights = [(a.allocated_amount / total_allocated) for a in allocations]
        hhi = sum(w * w for w in weights)  # Range 1/N to 1.0
        return round(hhi * 100.0, 2)

    @staticmethod
    def calculate_exposure_risk(
        total_allocated: float,
        total_capital: float,
    ) -> float:
        """Calculates exposure risk: Percentage of available capital deployed (0.0 to 100.0%)."""
        if total_capital <= 0:
            return 0.0
        return round(min(100.0, (total_allocated / total_capital) * 100.0), 2)

    @classmethod
    def calculate_portfolio_risk_score(
        cls,
        allocations: List[CapitalAllocation],
        concentration_risk: float,
        exposure_risk: float,
    ) -> float:
        """
        Computes comprehensive Portfolio Risk Score (0.0 to 100.0).
        Blend of:
        - Position quality risk (40%): Weighted average of position risk scores
        - Concentration risk (30%): Single-stock concentration penalty
        - Exposure risk (30%): Capital deployment exposure
        """
        if not allocations:
            return 0.0

        total_allocated = sum(a.allocated_amount for a in allocations)
        if total_allocated <= 0:
            return 0.0

        # Map RiskLevel to numeric severity
        risk_multipliers = {
            RiskLevel.LOW: 20.0,
            RiskLevel.MEDIUM: 45.0,
            RiskLevel.HIGH: 75.0,
            RiskLevel.VERY_HIGH: 95.0,
        }

        weighted_pos_risk = sum(
            risk_multipliers.get(a.risk_level, 50.0) * (a.allocated_amount / total_allocated)
            for a in allocations
        )

        composite_risk = (
            (weighted_pos_risk * 0.40)
            + (concentration_risk * 0.30)
            + (exposure_risk * 0.30)
        )
        return round(max(0.0, min(100.0, composite_risk)), 2)

    @staticmethod
    def assign_risk_category(risk_score: float) -> PortfolioRiskCategory:
        """Classifies aggregate risk score into standard risk category."""
        if risk_score <= 35.0:
            return PortfolioRiskCategory.LOW
        elif risk_score <= 55.0:
            return PortfolioRiskCategory.MEDIUM
        elif risk_score <= 75.0:
            return PortfolioRiskCategory.HIGH
        else:
            return PortfolioRiskCategory.VERY_HIGH
