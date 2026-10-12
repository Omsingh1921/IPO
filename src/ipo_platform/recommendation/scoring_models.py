"""
Scoring Models and Factor Evaluators for Indian IPO Recommendation Intelligence Engine.
Defines factor weights, categorical enums, and deterministic scoring curves for:
GMP, QIB/NII/Retail subscriptions, Revenue/PAT growth, ROE, Debt ratio, and P/E valuation.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional


class RecommendationCategory(str, Enum):
    """Categorical recommendation action for an IPO offering."""
    AVOID = "AVOID"
    NEUTRAL = "NEUTRAL"
    SUBSCRIBE = "SUBSCRIBE"
    STRONG_SUBSCRIBE = "STRONG_SUBSCRIBE"


class RiskLevel(str, Enum):
    """Overall investment risk classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class FactorScore:
    """Individual evaluation score for a quantitative IPO factor."""
    name: str
    raw_value: Optional[float]
    normalized_score: float  # 0.0 to 100.0
    weight: float            # e.g. 0.15 for 15%
    weighted_score: float    # normalized_score * weight
    description: str
    is_available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "normalized_score": round(self.normalized_score, 2),
            "weight": round(self.weight, 4),
            "weighted_score": round(self.weighted_score, 2),
            "description": self.description,
            "is_available": self.is_available,
        }


@dataclass
class FactorWeights:
    """
    Configurable factor weights distribution.
    Sum of weights must equal 1.0 (100%).
    """
    gmp: float = 0.15
    qib_subscription: float = 0.15
    nii_subscription: float = 0.05
    retail_subscription: float = 0.05
    revenue_growth: float = 0.10
    pat_growth: float = 0.10
    roe: float = 0.10
    debt_ratio: float = 0.05
    pe_valuation: float = 0.25

    def validate(self) -> None:
        total = (
            self.gmp
            + self.qib_subscription
            + self.nii_subscription
            + self.retail_subscription
            + self.revenue_growth
            + self.pat_growth
            + self.roe
            + self.debt_ratio
            + self.pe_valuation
        )
        if not math.isclose(total, 1.0, rel_tol=1e-3):
            raise ValueError(f"Sum of factor weights must equal 1.0, got {total:.4f}")


# --- Deterministic Factor Evaluators (0 to 100 Scale) ---

def score_gmp(gmp_percentage: Optional[float]) -> float:
    """
    Evaluates Grey Market Premium percentage.
    GMP >= 50% -> 100
    GMP 30% to 50% -> 80 to 100
    GMP 15% to 30% -> 60 to 80
    GMP 5% to 15% -> 40 to 60
    GMP 0% to 5% -> 25 to 40
    GMP < 0% (discount) -> 0 to 25
    """
    if gmp_percentage is None:
        return 50.0  # Neutral fallback when GMP is undisclosed

    if gmp_percentage >= 50.0:
        return 100.0
    elif gmp_percentage >= 30.0:
        return 80.0 + (gmp_percentage - 30.0) / 20.0 * 20.0
    elif gmp_percentage >= 15.0:
        return 60.0 + (gmp_percentage - 15.0) / 15.0 * 20.0
    elif gmp_percentage >= 5.0:
        return 40.0 + (gmp_percentage - 5.0) / 10.0 * 20.0
    elif gmp_percentage >= 0.0:
        return 25.0 + (gmp_percentage / 5.0) * 15.0
    elif gmp_percentage >= -20.0:
        # Discount range 0% to -20% -> 25 down to 0
        return max(0.0, 25.0 + (gmp_percentage / 20.0) * 25.0)
    else:
        return 0.0


def score_qib_subscription(multiple: Optional[float]) -> float:
    """
    Evaluates Qualified Institutional Buyer (QIB) subscription multiple.
    QIB >= 50x -> 100
    QIB 25x to 50x -> 85 to 100
    QIB 10x to 25x -> 70 to 85
    QIB 3x to 10x -> 50 to 70
    QIB 1x to 3x -> 30 to 50
    QIB < 1x -> 0 to 30
    """
    if multiple is None:
        return 50.0

    if multiple >= 50.0:
        return 100.0
    elif multiple >= 25.0:
        return 85.0 + (multiple - 25.0) / 25.0 * 15.0
    elif multiple >= 10.0:
        return 70.0 + (multiple - 10.0) / 15.0 * 15.0
    elif multiple >= 3.0:
        return 50.0 + (multiple - 3.0) / 7.0 * 20.0
    elif multiple >= 1.0:
        return 30.0 + (multiple - 1.0) / 2.0 * 20.0
    elif multiple > 0.0:
        return max(0.0, multiple * 30.0)
    else:
        return 0.0


def score_nii_subscription(multiple: Optional[float]) -> float:
    """
    Evaluates Non-Institutional / HNI subscription multiple.
    """
    if multiple is None:
        return 50.0

    if multiple >= 30.0:
        return 100.0
    elif multiple >= 10.0:
        return 75.0 + (multiple - 10.0) / 20.0 * 25.0
    elif multiple >= 3.0:
        return 50.0 + (multiple - 3.0) / 7.0 * 25.0
    elif multiple >= 1.0:
        return 30.0 + (multiple - 1.0) / 2.0 * 20.0
    elif multiple > 0.0:
        return max(0.0, multiple * 30.0)
    else:
        return 0.0


def score_retail_subscription(multiple: Optional[float]) -> float:
    """
    Evaluates Retail Individual Investor (RII) subscription multiple.
    """
    if multiple is None:
        return 50.0

    if multiple >= 10.0:
        return 100.0
    elif multiple >= 5.0:
        return 80.0 + (multiple - 5.0) / 5.0 * 20.0
    elif multiple >= 2.0:
        return 60.0 + (multiple - 2.0) / 3.0 * 20.0
    elif multiple >= 1.0:
        return 40.0 + (multiple - 1.0) * 20.0
    elif multiple > 0.0:
        return max(0.0, multiple * 40.0)
    else:
        return 0.0


def score_revenue_growth(growth_pct: Optional[float]) -> float:
    """
    Evaluates Year-over-Year revenue growth.
    >= 35% -> 100
    20% to 35% -> 80 to 100
    10% to 20% -> 60 to 80
    0% to 10% -> 40 to 60
    < 0% -> 0 to 40
    """
    if growth_pct is None:
        return 50.0

    if growth_pct >= 35.0:
        return 100.0
    elif growth_pct >= 20.0:
        return 80.0 + (growth_pct - 20.0) / 15.0 * 20.0
    elif growth_pct >= 10.0:
        return 60.0 + (growth_pct - 10.0) / 10.0 * 20.0
    elif growth_pct >= 0.0:
        return 40.0 + (growth_pct / 10.0) * 20.0
    elif growth_pct >= -20.0:
        return max(0.0, 40.0 + (growth_pct / 20.0) * 40.0)
    else:
        return 0.0


def score_pat_growth(growth_pct: Optional[float]) -> float:
    """
    Evaluates Year-over-Year Profit After Tax (PAT) growth.
    >= 40% -> 100
    25% to 40% -> 80 to 100
    10% to 25% -> 60 to 80
    0% to 10% -> 40 to 60
    < 0% -> 0 to 40
    """
    if growth_pct is None:
        return 50.0

    if growth_pct >= 40.0:
        return 100.0
    elif growth_pct >= 25.0:
        return 80.0 + (growth_pct - 25.0) / 15.0 * 20.0
    elif growth_pct >= 10.0:
        return 60.0 + (growth_pct - 10.0) / 15.0 * 20.0
    elif growth_pct >= 0.0:
        return 40.0 + (growth_pct / 10.0) * 20.0
    elif growth_pct >= -25.0:
        return max(0.0, 40.0 + (growth_pct / 25.0) * 40.0)
    else:
        return 0.0


def score_roe(roe_pct: Optional[float]) -> float:
    """
    Evaluates Return on Equity (ROE).
    >= 25% -> 100
    18% to 25% -> 80 to 100
    12% to 18% -> 60 to 80
    5% to 12% -> 40 to 60
    < 5% or negative -> 0 to 40
    """
    if roe_pct is None:
        return 50.0

    if roe_pct >= 25.0:
        return 100.0
    elif roe_pct >= 18.0:
        return 80.0 + (roe_pct - 18.0) / 7.0 * 20.0
    elif roe_pct >= 12.0:
        return 60.0 + (roe_pct - 12.0) / 6.0 * 20.0
    elif roe_pct >= 5.0:
        return 40.0 + (roe_pct - 5.0) / 7.0 * 20.0
    elif roe_pct > 0.0:
        return max(0.0, (roe_pct / 5.0) * 40.0)
    else:
        return 0.0


def score_debt_ratio(debt_equity: Optional[float]) -> float:
    """
    Evaluates Debt-to-Equity Ratio (Lower is healthier).
    <= 0.20 -> 100 (virtually debt free)
    0.20 to 0.50 -> 85 to 100
    0.50 to 1.00 -> 65 to 85
    1.00 to 2.00 -> 40 to 65
    2.00 to 3.00 -> 20 to 40
    > 3.00 -> 0 to 20
    """
    if debt_equity is None:
        return 50.0

    if debt_equity <= 0.20:
        return 100.0
    elif debt_equity <= 0.50:
        return 85.0 + (0.50 - debt_equity) / 0.30 * 15.0
    elif debt_equity <= 1.00:
        return 65.0 + (1.00 - debt_equity) / 0.50 * 20.0
    elif debt_equity <= 2.00:
        return 40.0 + (2.00 - debt_equity) / 1.00 * 25.0
    elif debt_equity <= 3.00:
        return 20.0 + (3.00 - debt_equity) / 1.00 * 20.0
    elif debt_equity <= 4.00:
        return max(0.0, 20.0 - (debt_equity - 3.00) * 20.0)
    else:
        return 0.0


def score_pe_valuation(
    issue_pe: Optional[float],
    benchmark_pe: Optional[float] = None,
) -> float:
    """
    Evaluates Price-to-Earnings valuation multiple.
    When benchmark_pe (industry or peer average) is present, evaluates relative spread.
    Otherwise evaluates on absolute reasonable Indian IPO multiple bands.
    """
    if issue_pe is None or issue_pe <= 0:
        return 40.0  # Penalize missing or loss-making P/E

    if benchmark_pe is not None and benchmark_pe > 0:
        # Relative spread: (benchmark_pe - issue_pe) / benchmark_pe
        spread_pct = ((benchmark_pe - issue_pe) / benchmark_pe) * 100.0
        # Positive spread means issue is discounted relative to peers
        if spread_pct >= 25.0:
            return 100.0
        elif spread_pct >= 10.0:
            return 80.0 + (spread_pct - 10.0) / 15.0 * 20.0
        elif spread_pct >= -10.0:
            # Fairly valued (-10% to +10%)
            return 60.0 + (spread_pct + 10.0) / 20.0 * 20.0
        elif spread_pct >= -25.0:
            # Moderate premium (+10% to +25%)
            return 40.0 + (spread_pct + 25.0) / 15.0 * 20.0
        elif spread_pct >= -50.0:
            # High premium (+25% to +50%)
            return 20.0 + (spread_pct + 50.0) / 25.0 * 20.0
        else:
            return 0.0

    # Absolute fallback
    if issue_pe <= 15.0:
        return 95.0
    elif issue_pe <= 25.0:
        return 80.0 + (25.0 - issue_pe) / 10.0 * 15.0
    elif issue_pe <= 35.0:
        return 65.0 + (35.0 - issue_pe) / 10.0 * 15.0
    elif issue_pe <= 50.0:
        return 45.0 + (50.0 - issue_pe) / 15.0 * 20.0
    elif issue_pe <= 75.0:
        return 20.0 + (75.0 - issue_pe) / 25.0 * 25.0
    else:
        return max(0.0, 20.0 - (issue_pe - 75.0) * 0.5)
