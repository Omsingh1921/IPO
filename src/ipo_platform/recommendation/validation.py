"""
Recommendation Validation Engine for Indian IPO Platform (Phase 10 - Stage 2).
Empirically evaluates the IPORecommendationEngine against historical post-listing outcomes.
Reuses existing IPORecommendationEngine, BacktestEngine, and HistoricalDataLoader without
duplicating recommendation or scoring logic.
"""

from datetime import datetime, timezone
import logging
import statistics
from typing import Any, Dict, List, Optional, Tuple

from ipo_platform.backtest.historical_data_loader import HistoricalDataLoader
from ipo_platform.models.schema import MasterIPORecord
from ipo_platform.recommendation.performance_metrics import (
    CategoryPerformance,
    RecommendationPerformanceReport,
)
from ipo_platform.recommendation.recommendation_engine import IPORecommendationEngine
from ipo_platform.recommendation.scoring_models import RecommendationCategory

logger = logging.getLogger(__name__)


class RecommendationValidationEngine:
    """
    Backtesting & Empirical Validation Engine for IPO Recommendations.
    Validates pre-listing algorithmic recommendations against historical post-listing
    empirical outcomes (listing day returns, max upsides, drawdowns).
    """

    def __init__(
        self,
        engine: Optional[IPORecommendationEngine] = None,
        strong_subscribe_success_min_return: float = 15.0,
        subscribe_success_min_return: float = 5.0,
        avoid_success_max_return: float = 5.0,
    ) -> None:
        """
        Initializes validation engine with configurable empirical benchmarks.
        :param engine: Instance of IPORecommendationEngine (or default initialized).
        :param strong_subscribe_success_min_return: Minimum % listing return to validate STRONG_SUBSCRIBE (default 15%).
        :param subscribe_success_min_return: Minimum % listing return to validate SUBSCRIBE (default 5%).
        :param avoid_success_max_return: Maximum % listing return to validate AVOID call (default <= 5%).
        """
        self.engine = engine or IPORecommendationEngine()
        self.strong_subscribe_success_min_return = strong_subscribe_success_min_return
        self.subscribe_success_min_return = subscribe_success_min_return
        self.avoid_success_max_return = avoid_success_max_return

    def validate_cohort(
        self,
        records: List[MasterIPORecord],
    ) -> RecommendationPerformanceReport:
        """
        Executes empirical validation across a cohort of MasterIPORecord instances.
        Filters for records containing verified historical post-listing outcomes,
        evaluates recommendations via IPORecommendationEngine, compares predicted actions
        with actual listing returns, and computes comprehensive statistical metrics.
        """
        # 1. Extract historical outcomes using HistoricalDataLoader
        historical_cohort = HistoricalDataLoader.load_historical_cohort(records)
        historical_ids = {c["ipo_id"] for c in historical_cohort}

        # Filter records matching historical cohort
        valid_records = [
            r for r in records
            if (hasattr(r, "ipo_entity") and r.ipo_entity.ipo_id in historical_ids)
            or (hasattr(r, "ipo_id") and getattr(r, "ipo_id") in historical_ids)
        ]

        if not valid_records:
            return RecommendationPerformanceReport(
                total_evaluated=len(records),
                historical_cohort_size=0,
                overall_accuracy=0.0,
                precision=None,
                recall=None,
                f1_score=None,
                win_rate=None,
                average_return=None,
                strong_subscribe_accuracy=None,
                avoid_accuracy=None,
                category_breakdown={},
                recommendation_distribution={
                    cat.value: 0 for cat in RecommendationCategory
                },
                cohort_details=[],
            )

        # Map historical outcome details by ipo_id
        outcomes_by_id = {c["ipo_id"]: c for c in historical_cohort}

        evaluated_items: List[Dict[str, Any]] = []
        distribution: Dict[str, int] = {cat.value: 0 for cat in RecommendationCategory}

        # Group outcomes by predicted category
        by_category: Dict[RecommendationCategory, List[Dict[str, Any]]] = {
            cat: [] for cat in RecommendationCategory
        }

        # 2. Evaluate each record using existing IPORecommendationEngine
        for rec in valid_records:
            rec_id = (
                rec.ipo_entity.ipo_id
                if hasattr(rec, "ipo_entity") and rec.ipo_entity
                else getattr(rec, "ipo_id", "UNKNOWN")
            )
            outcome = outcomes_by_id.get(rec_id, {})
            listing_return = outcome.get("listing_day_return_percent")

            # Execute recommendation engine without duplication
            rec_result = self.engine.evaluate(rec)
            predicted_cat = rec_result.recommendation
            distribution[predicted_cat.value] += 1

            is_correct = self._is_recommendation_correct(predicted_cat, listing_return)

            item = {
                "ipo_id": rec_id,
                "company_name": rec_result.company_name,
                "predicted_category": predicted_cat.value,
                "composite_score": rec_result.composite_score,
                "confidence_score": rec_result.confidence_score,
                "risk_level": rec_result.risk_level.value,
                "listing_day_return_percent": listing_return,
                "is_correct": is_correct,
                "veto_applied": rec_result.veto_applied,
            }
            evaluated_items.append(item)
            by_category[predicted_cat].append(item)

        # 3. Calculate Category Performance Breakdown
        category_breakdown: Dict[str, CategoryPerformance] = {}
        for cat, items in by_category.items():
            category_breakdown[cat.value] = self._calculate_category_performance(cat, items)

        # 4. Compute Aggregate Metrics
        all_returns = [
            item["listing_day_return_percent"]
            for item in evaluated_items
            if isinstance(item.get("listing_day_return_percent"), (int, float))
        ]
        overall_avg_return = (
            sum(all_returns) / len(all_returns) if all_returns else None
        )
        overall_win_rate = (
            (sum(1 for r in all_returns if r > 0) / len(all_returns)) * 100.0
            if all_returns
            else None
        )

        total_correct = sum(1 for item in evaluated_items if item["is_correct"])
        overall_accuracy = (
            (total_correct / len(evaluated_items)) * 100.0
            if evaluated_items
            else 0.0
        )

        # Strong Subscribe & Avoid Accuracy
        strong_sub_perf = category_breakdown.get(RecommendationCategory.STRONG_SUBSCRIBE.value)
        avoid_perf = category_breakdown.get(RecommendationCategory.AVOID.value)

        strong_subscribe_accuracy = (
            strong_sub_perf.success_rate if strong_sub_perf and strong_sub_perf.total_count > 0 else None
        )
        avoid_accuracy = (
            avoid_perf.success_rate if avoid_perf and avoid_perf.total_count > 0 else None
        )

        # Precision & Recall for Actionable Recommendations (STRONG_SUBSCRIBE & SUBSCRIBE)
        precision, recall, f1_score = self._calculate_precision_recall_f1(evaluated_items)

        return RecommendationPerformanceReport(
            total_evaluated=len(records),
            historical_cohort_size=len(evaluated_items),
            overall_accuracy=overall_accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            win_rate=overall_win_rate,
            average_return=overall_avg_return,
            strong_subscribe_accuracy=strong_subscribe_accuracy,
            avoid_accuracy=avoid_accuracy,
            category_breakdown=category_breakdown,
            recommendation_distribution=distribution,
            cohort_details=evaluated_items,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _is_recommendation_correct(
        self,
        category: RecommendationCategory,
        listing_return: Optional[float],
    ) -> bool:
        """
        Determines empirical correctness of a recommendation against actual outcome:
        - STRONG_SUBSCRIBE: Correct if listing_return >= strong_subscribe_success_min_return (default 15%).
        - SUBSCRIBE: Correct if listing_return >= subscribe_success_min_return (default 5%).
        - NEUTRAL: Correct if -5% <= listing_return <= +15% (range-bound moderate outcome).
        - AVOID: Correct if listing_return <= avoid_success_max_return (negative or weak listing <= 5%).
        """
        if listing_return is None:
            return False

        if category == RecommendationCategory.STRONG_SUBSCRIBE:
            return listing_return >= self.strong_subscribe_success_min_return
        elif category == RecommendationCategory.SUBSCRIBE:
            return listing_return >= self.subscribe_success_min_return
        elif category == RecommendationCategory.NEUTRAL:
            return -5.0 <= listing_return <= 15.0
        elif category == RecommendationCategory.AVOID:
            return listing_return <= self.avoid_success_max_return
        return False

    def _calculate_category_performance(
        self,
        category: RecommendationCategory,
        items: List[Dict[str, Any]],
    ) -> CategoryPerformance:
        """Calculates granular statistics for a single recommendation category cohort."""
        total_count = len(items)
        if total_count == 0:
            return CategoryPerformance(
                category=category,
                total_count=0,
                winning_count=0,
                losing_count=0,
                win_rate=None,
                average_return=None,
                median_return=None,
                max_return=None,
                min_return=None,
                success_rate=None,
            )

        returns = [
            it["listing_day_return_percent"]
            for it in items
            if isinstance(it.get("listing_day_return_percent"), (int, float))
        ]
        winning = sum(1 for r in returns if r > 0)
        losing = sum(1 for r in returns if r <= 0)
        win_rate = (winning / len(returns)) * 100.0 if returns else None
        avg_ret = sum(returns) / len(returns) if returns else None
        med_ret = statistics.median(returns) if returns else None
        max_ret = max(returns) if returns else None
        min_ret = min(returns) if returns else None

        successful_calls = sum(1 for it in items if it["is_correct"])
        success_rate = (successful_calls / total_count) * 100.0

        return CategoryPerformance(
            category=category,
            total_count=total_count,
            winning_count=winning,
            losing_count=losing,
            win_rate=win_rate,
            average_return=avg_ret,
            median_return=med_ret,
            max_return=max_ret,
            min_return=min_ret,
            success_rate=success_rate,
        )

    def _calculate_precision_recall_f1(
        self,
        items: List[Dict[str, Any]],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculates precision, recall, and F1-score for positive investment calls.
        Positive Class Prediction: (STRONG_SUBSCRIBE or SUBSCRIBE)
        Ground Truth Positive: Actual listing day return >= subscribe_success_min_return (5%).
        """
        tp = 0
        fp = 0
        fn = 0

        for it in items:
            cat = it["predicted_category"]
            ret = it.get("listing_day_return_percent")
            if not isinstance(ret, (int, float)):
                continue

            predicted_positive = cat in (
                RecommendationCategory.STRONG_SUBSCRIBE.value,
                RecommendationCategory.SUBSCRIBE.value,
            )
            actual_positive = ret >= self.subscribe_success_min_return

            if predicted_positive and actual_positive:
                tp += 1
            elif predicted_positive and not actual_positive:
                fp += 1
            elif not predicted_positive and actual_positive:
                fn += 1

        precision = ((tp / (tp + fp)) * 100.0) if (tp + fp) > 0 else None
        recall = ((tp / (tp + fn)) * 100.0) if (tp + fn) > 0 else None

        f1 = None
        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = (2 * precision * recall) / (precision + recall)

        return precision, recall, f1
