"""
Backtest Engine Orchestrator for Phase 4.
Evaluates historical IPO records and produces quantitative performance reports.
"""

from typing import Any, Dict, List
from ..models.schema import MasterIPORecord
from .historical_data_loader import HistoricalDataLoader
from .metrics import BacktestMetricsCalculator


class BacktestEngine:
    """Executes empirical backtests against historical IPO cohorts."""

    @classmethod
    def run_backtest(cls, records: List[MasterIPORecord]) -> Dict[str, Any]:
        """Runs complete backtesting simulation across a list of historical records."""
        cohort = HistoricalDataLoader.load_historical_cohort(records)

        if not cohort:
            return {
                "total_records_processed": len(records),
                "historical_cohort_size": 0,
                "win_rate_percent": None,
                "average_listing_return_percent": None,
                "scenario_accuracy": {},
            }

        win_rate = BacktestMetricsCalculator.calculate_win_rate(cohort)
        avg_return = BacktestMetricsCalculator.calculate_average_listing_return(cohort)
        accuracy_metrics = BacktestMetricsCalculator.calculate_scenario_precision_recall(cohort)

        return {
            "total_records_processed": len(records),
            "historical_cohort_size": len(cohort),
            "win_rate_percent": win_rate,
            "average_listing_return_percent": avg_return,
            "scenario_accuracy": accuracy_metrics,
            "cohort_details": cohort,
        }
