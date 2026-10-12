"""
Performance Metrics and Reporting Models for Recommendation Validation (Phase 10 - Stage 2).
Defines quantitative evaluation metrics:
- Recommendation Accuracy
- Precision & Recall
- Win Rate
- Average Listing Gain
- Category Performance Breakdown (STRONG_SUBSCRIBE, SUBSCRIBE, NEUTRAL, AVOID)
- Structured Report output contract
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ipo_platform.recommendation.scoring_models import RecommendationCategory


@dataclass
class CategoryPerformance:
    """Empirical performance metrics for a specific RecommendationCategory cohort."""
    category: RecommendationCategory
    total_count: int
    winning_count: int                  # listing_day_return > 0
    losing_count: int                   # listing_day_return <= 0
    win_rate: Optional[float]           # (winning_count / total_count) * 100
    average_return: Optional[float]     # average listing_day_return %
    median_return: Optional[float]      # median listing_day_return %
    max_return: Optional[float]
    min_return: Optional[float]
    success_rate: Optional[float]       # category-specific validation success rate %

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "total_count": self.total_count,
            "winning_count": self.winning_count,
            "losing_count": self.losing_count,
            "win_rate": round(self.win_rate, 2) if self.win_rate is not None else None,
            "average_return": round(self.average_return, 2) if self.average_return is not None else None,
            "median_return": round(self.median_return, 2) if self.median_return is not None else None,
            "max_return": round(self.max_return, 2) if self.max_return is not None else None,
            "min_return": round(self.min_return, 2) if self.min_return is not None else None,
            "success_rate": round(self.success_rate, 2) if self.success_rate is not None else None,
        }


@dataclass
class RecommendationPerformanceReport:
    """
    Comprehensive quantitative validation report assessing recommendation accuracy
    against actual post-listing empirical outcomes.
    """
    total_evaluated: int
    historical_cohort_size: int
    overall_accuracy: float                 # Percentage of correct calls across all categories
    precision: Optional[float]              # Precision for actionable calls (STRONG_SUBSCRIBE & SUBSCRIBE)
    recall: Optional[float]                 # Recall of profitable IPOs identified
    f1_score: Optional[float]
    win_rate: Optional[float]               # Overall cohort win rate %
    average_return: Optional[float]         # Overall cohort average listing return %
    strong_subscribe_accuracy: Optional[float] # % of STRONG_SUBSCRIBE that yielded >= benchmark gain
    avoid_accuracy: Optional[float]         # % of AVOID that yielded negative or sub-par returns
    category_breakdown: Dict[str, CategoryPerformance] = field(default_factory=dict)
    recommendation_distribution: Dict[str, int] = field(default_factory=dict)
    cohort_details: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the validation performance report to a JSON-compatible dictionary."""
        return {
            "overall_accuracy": round(self.overall_accuracy, 2),
            "strong_subscribe_accuracy": (
                round(self.strong_subscribe_accuracy, 2)
                if self.strong_subscribe_accuracy is not None
                else None
            ),
            "avoid_accuracy": (
                round(self.avoid_accuracy, 2)
                if self.avoid_accuracy is not None
                else None
            ),
            "average_return": (
                round(self.average_return, 2)
                if self.average_return is not None
                else None
            ),
            "precision": round(self.precision, 2) if self.precision is not None else None,
            "recall": round(self.recall, 2) if self.recall is not None else None,
            "f1_score": round(self.f1_score, 2) if self.f1_score is not None else None,
            "win_rate": round(self.win_rate, 2) if self.win_rate is not None else None,
            "total_evaluated": self.total_evaluated,
            "historical_cohort_size": self.historical_cohort_size,
            "recommendation_distribution": self.recommendation_distribution,
            "category_breakdown": {
                k: v.to_dict() for k, v in self.category_breakdown.items()
            },
            "generated_at": self.generated_at,
        }
