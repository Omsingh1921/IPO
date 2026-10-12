"""
Unit Tests for Recommendation Validation Engine & Performance Metrics (Phase 10 - Stage 2).
Validates:
- RecommendationValidationEngine against historical post-listing outcomes.
- Overall accuracy, Precision, Recall, F1 score, Win Rate, and Average Return.
- Category breakdowns (STRONG_SUBSCRIBE, SUBSCRIBE, NEUTRAL, AVOID).
- Strong Subscribe Success Rate and Avoid Success Rate.
- Integration with BacktestEngine and HistoricalDataLoader.
- Empty cohorts and unlisted IPO handling.
- JSON-compatible structured report output serialization.
"""

from datetime import date
import unittest

from ipo_platform.backtest.backtest_engine import BacktestEngine
from ipo_platform.backtest.historical_data_loader import HistoricalDataLoader
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.enums import DataCompletenessEnum, ListingStatusEnum, SourceTypeEnum
from ipo_platform.models.schema import (
    GMPData,
    HistoricalIPO,
    MasterIPORecord,
    SubscriptionCategory,
)
from ipo_platform.recommendation.performance_metrics import (
    CategoryPerformance,
    RecommendationPerformanceReport,
)
from ipo_platform.recommendation.recommendation_engine import IPORecommendationEngine
from ipo_platform.recommendation.scoring_models import RecommendationCategory, RiskLevel
from ipo_platform.recommendation.validation import RecommendationValidationEngine


class TestRecommendationValidationEngine(unittest.TestCase):
    """Test suite for empirical recommendation backtesting and validation."""

    def setUp(self):
        self.validation_engine = RecommendationValidationEngine()

    def _build_historical_record(
        self,
        ipo_id: str,
        company_name: str,
        gmp_pct: float,
        qib_multiple: float,
        nii_multiple: float,
        retail_multiple: float,
        rev_growth: float,
        pat_growth: float,
        roe: float,
        debt_ratio: float,
        pe: float,
        peer_pe: float,
        listing_day_return: float,
        max_upside: float = 40.0,
    ) -> MasterIPORecord:
        raw_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": ipo_id,
                "company_name": company_name,
                "company_legal_name": f"{company_name} Limited",
                "ticker_symbol": ipo_id.replace("-", "")[:8],
                "isin": f"INE{ipo_id[-6:]}0101",
                "segment": "Mainboard",
                "sector": "Industrials",
                "industry": "Manufacturing",
            },
            "ipo_status": {
                "status": "Listed",
                "research_date": "2026-01-10",
                "research_time": "10:00:00",
                "data_cutoff": "2026-01-10 09:30:00",
                "open_date": "2026-01-10",
                "close_date": "2026-01-12",
                "listing_date": "2026-01-18",
                "listing_status": "Listed",
            },
            "issue_structure": {
                "issue_size": {"value": 500.0, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_amount": {"value": 350.0, "unit": "Crores", "data_type": "Reported"},
                "ofs_amount": {"value": 150.0, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_percentage": {"value": 70.0, "data_type": "Calculated"},
                "ofs_percentage": {"value": 30.0, "data_type": "Calculated"},
                "face_value": {"value": 10.0, "data_type": "Reported"},
                "price_band_low": {"value": 190.0, "data_type": "Reported"},
                "price_band_high": {"value": 200.0, "data_type": "Reported"},
                "issue_price": {"value": 200.0, "data_type": "Reported"},
                "lot_size": {"value": 75, "data_type": "Reported"},
                "minimum_investment": {"value": 15000.0, "data_type": "Calculated"},
            },
            "financial_data": [
                {
                    "financial_period": "FY24",
                    "period_type": "FY",
                    "revenue_growth": {"value": rev_growth, "data_type": "Calculated"},
                    "PAT_growth": {"value": pat_growth, "data_type": "Calculated"},
                    "ROE": {"value": roe, "data_type": "Calculated"},
                    "debt_equity": {"value": debt_ratio, "data_type": "Calculated"},
                }
            ],
            "valuation_data": {
                "reference_price": 200.0,
                "reference_eps": 10.0,
                "issue_pe": {"value": pe, "data_type": "Calculated"},
                "peer_average_pe": {"value": peer_pe, "data_type": "Reported"},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-01-10",
            },
            "scenario_40_percent": {
                "reference_price": 200.0,
                "target_price": 280.0,
                "required_price_movement": 40.0,
                "target_pe": pe * 1.4,
                "supporting_factors": ["High demand"],
                "contradictory_factors": [],
                "scenario_status": "Supported",
                "scenario_methodology": "Standardized",
                "scenario_data_timestamp": "2026-01-10 10:00:00",
            },
            "data_quality": {
                "completeness_status": "Complete",
                "source_verification_status": "Verified",
                "last_verified": "2026-01-10 10:00:00",
            },
        }
        rec = JSONIngestor.from_dict(raw_json)
        rec.gmp_data = GMPData(
            gmp_value=gmp_pct * 2.0,
            gmp_percentage=gmp_pct,
            gmp_date="2026-01-10",
            gmp_time="10:00:00",
            reference_price=200.0,
            implied_price=200.0 * (1.0 + gmp_pct / 100.0),
            source="TestGMP",
        )
        rec.subscription_data = {
            "QIB": SubscriptionCategory(
                shares_offered=100000,
                shares_bid=int(100000 * qib_multiple),
                subscription_multiple=qib_multiple,
                source="Exchange",
                source_date="2026-01-12",
                retrieval_timestamp="2026-01-12 17:00:00",
            ),
            "NII": SubscriptionCategory(
                shares_offered=100000,
                shares_bid=int(100000 * nii_multiple),
                subscription_multiple=nii_multiple,
                source="Exchange",
                source_date="2026-01-12",
                retrieval_timestamp="2026-01-12 17:00:00",
            ),
            "Retail": SubscriptionCategory(
                shares_offered=100000,
                shares_bid=int(100000 * retail_multiple),
                subscription_multiple=retail_multiple,
                source="Exchange",
                source_date="2026-01-12",
                retrieval_timestamp="2026-01-12 17:00:00",
            ),
        }
        rec.historical_ipo = HistoricalIPO(
            historical_ipo=True,
            ipo_year=2026,
            listing_price=200.0 * (1.0 + listing_day_return / 100.0),
            listing_day_close=200.0 * (1.0 + listing_day_return / 100.0),
            listing_day_return=listing_day_return,
            max_upside_from_issue_price=max_upside,
        )
        return rec

    def test_empty_cohort_validation(self):
        report = self.validation_engine.validate_cohort([])
        self.assertEqual(report.total_evaluated, 0)
        self.assertEqual(report.historical_cohort_size, 0)
        self.assertEqual(report.overall_accuracy, 0.0)
        self.assertIsNone(report.win_rate)
        self.assertIsNone(report.average_return)
        self.assertIsNone(report.precision)

    def test_unlisted_records_ignored(self):
        rec = self._build_historical_record(
            "UNLIST-01", "Unlisted Ltd", 20.0, 5.0, 3.0, 2.0, 15.0, 15.0, 15.0, 0.5, 20.0, 25.0, 10.0
        )
        rec.historical_ipo = None  # No historical post-listing outcome

        report = self.validation_engine.validate_cohort([rec])
        self.assertEqual(report.total_evaluated, 1)
        self.assertEqual(report.historical_cohort_size, 0)

    def test_historical_cohort_evaluation_and_metrics(self):
        # 1. Strong Subscribe candidate that listed with +45% return (Correct)
        rec_strong = self._build_historical_record(
            ipo_id="STRONG-01",
            company_name="Mega Tech Ltd",
            gmp_pct=55.0,
            qib_multiple=55.0,
            nii_multiple=35.0,
            retail_multiple=10.0,
            rev_growth=40.0,
            pat_growth=45.0,
            roe=28.0,
            debt_ratio=0.1,
            pe=18.0,
            peer_pe=32.0,
            listing_day_return=45.0,
        )

        # 2. Subscribe candidate that listed with +18% return (Correct)
        rec_sub = self._build_historical_record(
            ipo_id="SUB-01",
            company_name="Good Growth Ltd",
            gmp_pct=22.0,
            qib_multiple=8.0,
            nii_multiple=5.0,
            retail_multiple=3.0,
            rev_growth=18.0,
            pat_growth=20.0,
            roe=16.0,
            debt_ratio=0.6,
            pe=25.0,
            peer_pe=30.0,
            listing_day_return=18.0,
        )

        # 3. Neutral candidate that listed flat at +2% return (Correct)
        rec_neutral = self._build_historical_record(
            ipo_id="NEU-01",
            company_name="Steady Co Ltd",
            gmp_pct=6.0,
            qib_multiple=2.5,
            nii_multiple=1.5,
            retail_multiple=1.2,
            rev_growth=8.0,
            pat_growth=6.0,
            roe=8.0,
            debt_ratio=1.4,
            pe=35.0,
            peer_pe=32.0,
            listing_day_return=2.0,
        )

        # 4. Avoid candidate that listed at -12% discount (Correct)
        rec_avoid = self._build_historical_record(
            ipo_id="AVOID-01",
            company_name="Toxic Debt Ltd",
            gmp_pct=-10.0,
            qib_multiple=0.6,
            nii_multiple=0.4,
            retail_multiple=0.5,
            rev_growth=-5.0,
            pat_growth=-10.0,
            roe=2.0,
            debt_ratio=3.8,
            pe=65.0,
            peer_pe=25.0,
            listing_day_return=-12.0,
        )

        cohort = [rec_strong, rec_sub, rec_neutral, rec_avoid]
        report = self.validation_engine.validate_cohort(cohort)

        # Basic cohort validation
        self.assertEqual(report.total_evaluated, 4)
        self.assertEqual(report.historical_cohort_size, 4)

        # All 4 recommendations were empirically correct
        self.assertEqual(report.overall_accuracy, 100.0)
        self.assertEqual(report.strong_subscribe_accuracy, 100.0)
        self.assertEqual(report.avoid_accuracy, 100.0)

        # Win rate: 3 positive returns (45%, 18%, 2%) out of 4 = 75%
        self.assertEqual(report.win_rate, 75.0)

        # Average listing return: (45 + 18 + 2 - 12) / 4 = 53 / 4 = 13.25%
        self.assertAlmostEqual(report.average_return, 13.25, places=2)

        # Precision & Recall for actionable calls (STRONG_SUBSCRIBE & SUBSCRIBE)
        # 2 actionable calls, both > 5% listing gain -> Precision 100%, Recall 100%
        self.assertEqual(report.precision, 100.0)
        self.assertEqual(report.recall, 100.0)
        self.assertEqual(report.f1_score, 100.0)

        # Distribution verification
        self.assertEqual(report.recommendation_distribution[RecommendationCategory.STRONG_SUBSCRIBE.value], 1)
        self.assertEqual(report.recommendation_distribution[RecommendationCategory.SUBSCRIBE.value], 1)
        self.assertEqual(report.recommendation_distribution[RecommendationCategory.NEUTRAL.value], 1)
        self.assertEqual(report.recommendation_distribution[RecommendationCategory.AVOID.value], 1)

        # Category breakdown checks
        cat_strong = report.category_breakdown[RecommendationCategory.STRONG_SUBSCRIBE.value]
        self.assertEqual(cat_strong.total_count, 1)
        self.assertEqual(cat_strong.winning_count, 1)
        self.assertEqual(cat_strong.average_return, 45.0)
        self.assertEqual(cat_strong.success_rate, 100.0)

        cat_avoid = report.category_breakdown[RecommendationCategory.AVOID.value]
        self.assertEqual(cat_avoid.total_count, 1)
        self.assertEqual(cat_avoid.losing_count, 1)
        self.assertEqual(cat_avoid.average_return, -12.0)
        self.assertEqual(cat_avoid.success_rate, 100.0)

    def test_structured_report_serialization(self):
        rec_strong = self._build_historical_record(
            "STRONG-01", "Mega Tech Ltd", 55.0, 55.0, 35.0, 10.0, 40.0, 45.0, 28.0, 0.1, 18.0, 32.0, 45.0
        )
        report = self.validation_engine.validate_cohort([rec_strong])
        report_dict = report.to_dict()

        # Contract requirements validation
        self.assertIn("overall_accuracy", report_dict)
        self.assertIn("strong_subscribe_accuracy", report_dict)
        self.assertIn("avoid_accuracy", report_dict)
        self.assertIn("average_return", report_dict)
        self.assertIn("recommendation_distribution", report_dict)
        self.assertIn("category_breakdown", report_dict)

        self.assertEqual(report_dict["overall_accuracy"], 100.0)
        self.assertEqual(report_dict["strong_subscribe_accuracy"], 100.0)
        self.assertEqual(report_dict["average_return"], 45.0)

    def test_backtest_engine_coexistence(self):
        """Ensures that BacktestEngine and HistoricalDataLoader remain fully compatible."""
        rec = self._build_historical_record(
            "BTEST-01", "Existing Backtest Co", 30.0, 10.0, 5.0, 2.0, 20.0, 20.0, 20.0, 0.5, 20.0, 25.0, 25.0
        )
        # Execute original Phase 4 BacktestEngine
        p4_result = BacktestEngine.run_backtest([rec])
        self.assertEqual(p4_result["historical_cohort_size"], 1)
        self.assertEqual(p4_result["win_rate_percent"], 100.0)
        self.assertEqual(p4_result["average_listing_return_percent"], 25.0)

        # Execute Phase 10 RecommendationValidationEngine on the same record
        p10_report = self.validation_engine.validate_cohort([rec])
        self.assertEqual(p10_report.historical_cohort_size, 1)
        self.assertEqual(p10_report.win_rate, 100.0)
        self.assertEqual(p10_report.average_return, 25.0)


if __name__ == "__main__":
    unittest.main()
