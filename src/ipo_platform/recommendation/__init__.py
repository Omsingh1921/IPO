"""
Recommendation Intelligence Package for Indian IPO Platform.
Exposes recommendation models, factor scores, risk metrics, and the recommendation engine.
"""

from ipo_platform.recommendation.performance_metrics import (
    CategoryPerformance,
    RecommendationPerformanceReport,
)
from ipo_platform.recommendation.recommendation_engine import IPORecommendationEngine
from ipo_platform.recommendation.recommendation_result import RecommendationResult
from ipo_platform.recommendation.scoring_models import (
    FactorScore,
    FactorWeights,
    RecommendationCategory,
    RiskLevel,
    score_debt_ratio,
    score_gmp,
    score_nii_subscription,
    score_pat_growth,
    score_pe_valuation,
    score_qib_subscription,
    score_retail_subscription,
    score_revenue_growth,
    score_roe,
)
from ipo_platform.recommendation.validation import RecommendationValidationEngine

__all__ = [
    "IPORecommendationEngine",
    "RecommendationValidationEngine",
    "RecommendationResult",
    "RecommendationPerformanceReport",
    "CategoryPerformance",
    "RecommendationCategory",
    "RiskLevel",
    "FactorScore",
    "FactorWeights",
    "score_gmp",
    "score_qib_subscription",
    "score_nii_subscription",
    "score_retail_subscription",
    "score_revenue_growth",
    "score_pat_growth",
    "score_roe",
    "score_debt_ratio",
    "score_pe_valuation",
]
