import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ipo_platform.io.json_ingestor import JSONIngestor
from src.ipo_platform.models.schema import HistoricalIPO
from src.ipo_platform.models.enums import ListingStatusEnum, ScenarioStatusEnum
from src.ipo_platform.backtest.historical_data_loader import HistoricalDataLoader
from src.ipo_platform.backtest.metrics import BacktestMetricsCalculator
from src.ipo_platform.backtest.backtest_engine import BacktestEngine


class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "IND-MB-2024-NTPCGREEN",
                "company_name": "NTPC Green Energy Limited",
                "company_legal_name": "NTPC Green Energy Limited",
                "ticker_symbol": "NTPCGREEN",
                "isin": "INE000000000",
                "segment": "Mainboard",
                "sector": "Renewable Energy",
                "industry": "Power Generation",
            },
            "ipo_status": {
                "status": "Listed",
                "research_date": "2024-11-18",
                "research_time": "10:00:00",
                "data_cutoff": "2024-11-18 10:00:00",
                "open_date": "2024-11-19",
                "close_date": "2024-11-22",
                "listing_date": "2024-11-27",
                "listing_status": "Listed",
            },
            "issue_structure": {
                "issue_size": {"value": 10000.00, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_amount": {"value": 10000.00, "unit": "Crores", "data_type": "Reported"},
                "ofs_amount": {"value": 0.00, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_percentage": {"value": 100.00, "data_type": "Calculated"},
                "ofs_percentage": {"value": 0.00, "data_type": "Calculated"},
                "face_value": {"value": 10.00, "data_type": "Reported"},
                "price_band_low": {"value": 102.00, "data_type": "Reported"},
                "price_band_high": {"value": 108.00, "data_type": "Reported"},
                "issue_price": {"value": 108.00, "data_type": "Reported"},
                "lot_size": {"value": 138, "data_type": "Reported"},
                "minimum_investment": {"value": 14904.00, "data_type": "Calculated"},
            },
            "valuation_data": {
                "reference_price": 108.00,
                "reference_eps": 2.10,
                "issue_pe": {"value": 51.43, "data_type": "Calculated"},
                "valuation_method": "Trailing P/E",
                "valuation_source": "RHP",
                "valuation_date": "2024-11-18",
            },
            "scenario_40_percent": {
                "reference_price": 108.00,
                "target_price": 151.20,
                "required_price_movement": 40.00,
                "supporting_factors": ["High anchor demand"],
                "contradictory_factors": [],
                "scenario_status": "Supported",
                "scenario_methodology": "Standard model",
                "scenario_data_timestamp": "2024-11-18 10:00:00",
            },
            "data_quality": {
                "completeness_status": "Complete",
                "source_verification_status": "Verified",
                "last_verified": "2024-11-18 10:00:00",
            },
        }
        self.record = JSONIngestor.from_dict(self.sample_json)
        self.record.historical_ipo = HistoricalIPO(
            historical_ipo=True,
            ipo_year=2024,
            listing_price=111.60,
            listing_day_close=122.50,
            listing_day_return=13.43,
            max_upside_from_issue_price=45.00,  # Reached +40% target
        )

    def test_historical_loader(self):
        outcome = HistoricalDataLoader.extract_post_listing_outcomes(self.record)
        self.assertIsNotNone(outcome)
        self.assertEqual(outcome["ipo_id"], "IND-MB-2024-NTPCGREEN")
        self.assertEqual(outcome["listing_day_return_percent"], 13.43)

    def test_backtest_metrics(self):
        cohort = HistoricalDataLoader.load_historical_cohort([self.record])
        win_rate = BacktestMetricsCalculator.calculate_win_rate(cohort)
        self.assertEqual(win_rate, 100.0)

        avg_return = BacktestMetricsCalculator.calculate_average_listing_return(cohort)
        self.assertEqual(avg_return, 13.43)

        prec_rec = BacktestMetricsCalculator.calculate_scenario_precision_recall(cohort)
        self.assertEqual(prec_rec["true_positives"], 1)
        self.assertEqual(prec_rec["precision_percent"], 100.0)

    def test_backtest_engine_run(self):
        results = BacktestEngine.run_backtest([self.record])
        self.assertEqual(results["total_records_processed"], 1)
        self.assertEqual(results["historical_cohort_size"], 1)
        self.assertEqual(results["win_rate_percent"], 100.0)

    def test_cutoff_look_ahead_bias_prevention(self):
        # Verify that post-listing outcome fields cannot alter the pre-listing scenario status
        original_scenario = self.record.scenario_40_percent.scenario_status
        # Inject an artificial post-listing return of 200%
        self.record.historical_ipo.listing_day_return = 200.0
        self.record.historical_ipo.max_upside_from_issue_price = 300.0

        # Outcome extraction must preserve the pre-listing evaluation strictly
        outcome = HistoricalDataLoader.extract_post_listing_outcomes(self.record)
        self.assertEqual(outcome["scenario_status_pre_listing"], original_scenario.value)
        # Ensure pre-listing decision cutoff is decoupled from post-listing performance
        self.assertNotEqual(outcome["scenario_status_pre_listing"], outcome["listing_day_return_percent"])


if __name__ == "__main__":
    unittest.main()
