"""
Portfolio Strategy and Capital Allocation Data Models (Phase 10 - Stage 3).
Defines:
- RiskProfile (CONSERVATIVE, MODERATE, AGGRESSIVE)
- PortfolioRiskCategory (LOW, MEDIUM, HIGH, VERY_HIGH)
- AllocationStrategy
- CapitalAllocation
- PortfolioRecommendation
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional

from ipo_platform.recommendation.scoring_models import RecommendationCategory, RiskLevel


class RiskProfile(str, Enum):
    """Investor risk tolerance and strategy profile."""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class PortfolioRiskCategory(str, Enum):
    """Portfolio overall risk classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class AllocationStrategy:
    """Strategy matrix defining capital percentages per category and profile."""
    profile: RiskProfile
    max_single_ipo_pct: float = 35.0          # Max 35% in any single IPO
    max_sector_concentration_pct: float = 40.0 # Max 40% in any single sector
    max_total_allocation_pct: float = 100.0   # Max 100% total portfolio allocation

    # Allocation weights by recommendation category:
    # Strong Subscribe: Aggressive 35%, Moderate 25%, Conservative 15%
    # Subscribe:        Aggressive 20%, Moderate 15%, Conservative 10%
    # Neutral:          Aggressive 10%, Moderate 5%, Conservative 0%
    # Avoid:            Always 0%
    def get_base_allocation_pct(self, recommendation: RecommendationCategory) -> float:
        """Determines base allocation percentage from strategy rules."""
        if recommendation == RecommendationCategory.AVOID:
            return 0.0

        if self.profile == RiskProfile.AGGRESSIVE:
            if recommendation == RecommendationCategory.STRONG_SUBSCRIBE:
                return 35.0
            elif recommendation == RecommendationCategory.SUBSCRIBE:
                return 20.0
            elif recommendation == RecommendationCategory.NEUTRAL:
                return 10.0
        elif self.profile == RiskProfile.MODERATE:
            if recommendation == RecommendationCategory.STRONG_SUBSCRIBE:
                return 25.0
            elif recommendation == RecommendationCategory.SUBSCRIBE:
                return 15.0
            elif recommendation == RecommendationCategory.NEUTRAL:
                return 5.0
        elif self.profile == RiskProfile.CONSERVATIVE:
            if recommendation == RecommendationCategory.STRONG_SUBSCRIBE:
                return 15.0
            elif recommendation == RecommendationCategory.SUBSCRIBE:
                return 10.0
            elif recommendation == RecommendationCategory.NEUTRAL:
                return 0.0

        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.value,
            "max_single_ipo_pct": self.max_single_ipo_pct,
            "max_sector_concentration_pct": self.max_sector_concentration_pct,
            "max_total_allocation_pct": self.max_total_allocation_pct,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class CapitalAllocation:
    """Quantitative capital allocation details for an individual IPO position."""
    ipo_id: str
    company_name: str
    sector: str
    recommendation: RecommendationCategory
    composite_score: float
    allocated_amount: float            # In currency units (e.g., INR)
    allocation_percentage: float       # Suggested allocation % of total capital (0-100)
    position_size: float               # Suggested position size in currency
    portfolio_weight: float            # Actual weight in portfolio (allocated_amount / total_allocated or total_capital)
    expected_return: float             # Expected return %
    expected_risk: float               # Expected risk score / volatility %
    risk_level: RiskLevel
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ipo_id": self.ipo_id,
            "company_name": self.company_name,
            "sector": self.sector,
            "recommendation": self.recommendation.value,
            "composite_score": round(self.composite_score, 2),
            "allocated_amount": round(self.allocated_amount, 2),
            "allocation_percentage": round(self.allocation_percentage, 2),
            "position_size": round(self.position_size, 2),
            "portfolio_weight": round(self.portfolio_weight, 4),
            "expected_return": round(self.expected_return, 2),
            "expected_risk": round(self.expected_risk, 2),
            "risk_level": self.risk_level.value,
            "rationale": self.rationale,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class PortfolioRecommendation:
    """
    Holistic portfolio-level capital allocation and risk management output.
    Contains position breakdowns, capital metrics, risk scoring, and diversification limits.
    """
    total_capital: float
    total_allocated_capital: float
    unallocated_cash: float
    total_allocation_percentage: float   # Sum of allocation percentages (<= 100%)
    risk_profile: RiskProfile
    allocations: List[CapitalAllocation] = field(default_factory=list)
    sector_allocations: Dict[str, float] = field(default_factory=dict)  # Sector -> % of total capital
    portfolio_risk_score: float = 0.0    # 0.0 to 100.0 aggregate risk
    concentration_risk: float = 0.0     # Herfindahl-Hirschman index or top position ratio
    exposure_risk: float = 0.0          # Capital at risk ratio %
    portfolio_risk_category: PortfolioRiskCategory = PortfolioRiskCategory.MEDIUM
    expected_return: float = 0.0        # Weighted expected return %
    expected_risk: float = 0.0          # Weighted expected risk %
    sharpe_score: float = 0.0           # Sharpe-like risk-adjusted reward metric
    diversification_notes: List[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_capital": round(self.total_capital, 2),
            "total_allocated_capital": round(self.total_allocated_capital, 2),
            "unallocated_cash": round(self.unallocated_cash, 2),
            "total_allocation_percentage": round(self.total_allocation_percentage, 2),
            "risk_profile": self.risk_profile.value,
            "portfolio_risk_score": round(self.portfolio_risk_score, 2),
            "concentration_risk": round(self.concentration_risk, 2),
            "exposure_risk": round(self.exposure_risk, 2),
            "portfolio_risk_category": self.portfolio_risk_category.value,
            "expected_return": round(self.expected_return, 2),
            "expected_risk": round(self.expected_risk, 2),
            "sharpe_score": round(self.sharpe_score, 2),
            "sector_allocations": {k: round(v, 2) for k, v in self.sector_allocations.items()},
            "allocations": [a.to_dict() for a in self.allocations],
            "diversification_notes": self.diversification_notes,
            "generated_at": self.generated_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
