"""
Recommendation Result Container and Diagnostic Report Structures for Indian IPO Platform.
Defines RecommendationResult with composite scores, confidence ratings, risk classifications,
and detailed qualitative and quantitative rationale breakdown.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ipo_platform.recommendation.scoring_models import (
    FactorScore,
    RecommendationCategory,
    RiskLevel,
)


@dataclass
class RecommendationResult:
    """Complete quantitative recommendation output for an evaluated IPO."""
    ipo_id: str
    company_name: str
    recommendation: RecommendationCategory
    composite_score: float         # 0.0 to 100.0
    confidence_score: float        # 0.0 to 1.0 (or 0% to 100%)
    risk_level: RiskLevel
    factor_scores: Dict[str, FactorScore]
    strengths: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    veto_applied: Optional[str] = None
    summary_rationale: str = ""
    evaluation_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the recommendation result into a dictionary."""
        return {
            "ipo_id": self.ipo_id,
            "company_name": self.company_name,
            "recommendation": self.recommendation.value,
            "composite_score": round(self.composite_score, 2),
            "confidence_score": round(self.confidence_score, 2),
            "risk_level": self.risk_level.value,
            "factor_scores": {k: v.to_dict() for k, v in self.factor_scores.items()},
            "strengths": self.strengths,
            "risks": self.risks,
            "veto_applied": self.veto_applied,
            "summary_rationale": self.summary_rationale,
            "evaluation_timestamp": self.evaluation_timestamp,
        }
