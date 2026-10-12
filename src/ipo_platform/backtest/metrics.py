"""
Backtest Metrics Calculator Module.
Computes Win Rate, Average Returns, Precision, Recall, and Risk-Reward Ratios for historical cohorts.
"""

from typing import Any, Dict, List, Optional


class BacktestMetricsCalculator:
    """Computes empirical accuracy and statistical performance metrics for historical IPO cohorts."""

    @staticmethod
    def calculate_win_rate(cohort: List[Dict[str, Any]]) -> Optional[float]:
        """Calculates percentage of IPOs with positive listing day gains (%):

        (positive_listing_count / total_listed) * 100
        """
        valid_returns = [
            c["listing_day_return_percent"]
            for c in cohort
            if isinstance(c.get("listing_day_return_percent"), (int, float))
        ]
        if not valid_returns:
            return None
        positive_count = sum(1 for r in valid_returns if r > 0)
        return round((positive_count / len(valid_returns)) * 100.0, 2)

    @staticmethod
    def calculate_average_listing_return(cohort: List[Dict[str, Any]]) -> Optional[float]:
        """Calculates average listing day return percentage across cohort."""
        valid_returns = [
            c["listing_day_return_percent"]
            for c in cohort
            if isinstance(c.get("listing_day_return_percent"), (int, float))
        ]
        if not valid_returns:
            return None
        return round(sum(valid_returns) / len(valid_returns), 2)

    @staticmethod
    def calculate_scenario_precision_recall(
        cohort: List[Dict[str, Any]]
    ) -> Dict[str, Optional[float]]:
        """Calculates Precision and Recall for +40% Target Scenario classifications.

        Precision = (True Positives) / (True Positives + False Positives)
        Recall    = (True Positives) / (True Positives + False Negatives)
        """
        tp = 0  # Flagged Supported AND reached +40%
        fp = 0  # Flagged Supported BUT failed +40%
        fn = 0  # Flagged Not Supported / Insufficient BUT reached +40%

        for c in cohort:
            status = c.get("scenario_status_pre_listing")
            max_up = c.get("max_upside_percent")
            listing_ret = c.get("listing_day_return_percent")

            # Actual success if max_upside or listing return reached >= 40%
            reached_target = False
            if isinstance(max_up, (int, float)) and max_up >= 40.0:
                reached_target = True
            elif isinstance(listing_ret, (int, float)) and listing_ret >= 40.0:
                reached_target = True

            if status == "Supported":
                if reached_target:
                    tp += 1
                else:
                    fp += 1
            else:
                if reached_target:
                    fn += 1

        precision = round((tp / (tp + fp)) * 100.0, 2) if (tp + fp) > 0 else None
        recall = round((tp / (tp + fn)) * 100.0, 2) if (tp + fn) > 0 else None

        return {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision_percent": precision,
            "recall_percent": recall,
        }
