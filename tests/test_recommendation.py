"""
Unit Tests for Recommendation Intelligence Engine (Phase 10 - Stage 1).
Validates:
- All 9 quantitative factor scoring curves.
- Composite score normalization (0-100).
- Recommendation categories: AVOID, NEUTRAL, SUBSCRIBE, STRONG_SUBSCRIBE.
- Critical red-flag veto enforcement.
- Confidence score calculation and data completeness degradation.
- Risk level classifications.
- Serialization and backward compatibility.
"""

from datetime import date
import unittest

from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.enums import DataCompletenessEnum, SourceTypeEnum
from ipo_platform.models.schema import (
    DataQuality,
    FinancialRecord,
    GMPData,
    IPOEntity,
    IPOStatus,
    IssueStructure,
    MasterIPORecord,
    ProvenanceEnvelope,
    Scenario40Percent,
    SubscriptionCategory,
    ValuationData,
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


class TestFactorEvaluators(unittest.TestCase):
    """Tests the 9 individual scoring curves."""

    def test_score_gmp(self):
        self.assertEqual(score_gmp(None), 50.0)
        self.assertEqual(score_gmp(60.0), 100.0)
        self.assertEqual(score_gmp(50.0), 100.0)
        self.assertAlmostEqual(score_gmp(40.0), 90.0)
        self.assertAlmostEqual(score_gmp(20.0), 66.666, places=2)
        self.assertAlmostEqual(score_gmp(10.0), 50.0)
        self.assertAlmostEqual(score_gmp(2.5), 32.5)
        self.assertAlmostEqual(score_gmp(0.0), 25.0)
        self.assertAlmostEqual(score_gmp(-10.0), 12.5)
        self.assertEqual(score_gmp(-25.0), 0.0)

    def test_score_qib_subscription(self):
        self.assertEqual(score_qib_subscription(None), 50.0)
        self.assertEqual(score_qib_subscription(60.0), 100.0)
        self.assertEqual(score_qib_subscription(50.0), 100.0)
        self.assertAlmostEqual(score_qib_subscription(25.0), 85.0)
        self.assertAlmostEqual(score_qib_subscription(10.0), 70.0)
        self.assertAlmostEqual(score_qib_subscription(3.0), 50.0)
        self.assertAlmostEqual(score_qib_subscription(1.0), 30.0)
        self.assertAlmostEqual(score_qib_subscription(0.5), 15.0)
        self.assertEqual(score_qib_subscription(0.0), 0.0)

    def test_score_nii_subscription(self):
        self.assertEqual(score_nii_subscription(None), 50.0)
        self.assertEqual(score_nii_subscription(35.0), 100.0)
        self.assertEqual(score_nii_subscription(10.0), 75.0)
        self.assertEqual(score_nii_subscription(3.0), 50.0)
        self.assertEqual(score_nii_subscription(1.0), 30.0)
        self.assertEqual(score_nii_subscription(0.0), 0.0)

    def test_score_retail_subscription(self):
        self.assertEqual(score_retail_subscription(None), 50.0)
        self.assertEqual(score_retail_subscription(15.0), 100.0)
        self.assertEqual(score_retail_subscription(5.0), 80.0)
        self.assertEqual(score_retail_subscription(2.0), 60.0)
        self.assertEqual(score_retail_subscription(1.0), 40.0)
        self.assertEqual(score_retail_subscription(0.0), 0.0)

    def test_score_revenue_growth(self):
        self.assertEqual(score_revenue_growth(None), 50.0)
        self.assertEqual(score_revenue_growth(40.0), 100.0)
        self.assertEqual(score_revenue_growth(20.0), 80.0)
        self.assertEqual(score_revenue_growth(10.0), 60.0)
        self.assertEqual(score_revenue_growth(0.0), 40.0)
        self.assertAlmostEqual(score_revenue_growth(-10.0), 20.0)
        self.assertEqual(score_revenue_growth(-25.0), 0.0)

    def test_score_pat_growth(self):
        self.assertEqual(score_pat_growth(None), 50.0)
        self.assertEqual(score_pat_growth(45.0), 100.0)
        self.assertEqual(score_pat_growth(25.0), 80.0)
        self.assertEqual(score_pat_growth(10.0), 60.0)
        self.assertEqual(score_pat_growth(0.0), 40.0)
        self.assertAlmostEqual(score_pat_growth(-12.5), 20.0)
        self.assertEqual(score_pat_growth(-30.0), 0.0)

    def test_score_roe(self):
        self.assertEqual(score_roe(None), 50.0)
        self.assertEqual(score_roe(30.0), 100.0)
        self.assertEqual(score_roe(18.0), 80.0)
        self.assertEqual(score_roe(12.0), 60.0)
        self.assertEqual(score_roe(5.0), 40.0)
        self.assertAlmostEqual(score_roe(2.5), 20.0)
        self.assertEqual(score_roe(-5.0), 0.0)

    def test_score_debt_ratio(self):
        self.assertEqual(score_debt_ratio(None), 50.0)
        self.assertEqual(score_debt_ratio(0.10), 100.0)
        self.assertEqual(score_debt_ratio(0.50), 85.0)
        self.assertEqual(score_debt_ratio(1.00), 65.0)
        self.assertEqual(score_debt_ratio(2.00), 40.0)
        self.assertEqual(score_debt_ratio(3.00), 20.0)
        self.assertEqual(score_debt_ratio(4.50), 0.0)

    def test_score_pe_valuation(self):
        self.assertEqual(score_pe_valuation(None), 40.0)
        self.assertEqual(score_pe_valuation(-5.0), 40.0)
        # Relative benchmark: issue 20 vs peer 30 -> 33% discount
        self.assertEqual(score_pe_valuation(20.0, 30.0), 100.0)
        # Relative benchmark: issue 40 vs peer 30 -> -33% premium
        self.assertAlmostEqual(score_pe_valuation(40.0, 30.0), 33.333, places=2)
        # Absolute benchmark
        self.assertEqual(score_pe_valuation(14.0, None), 95.0)
        self.assertEqual(score_pe_valuation(25.0, None), 80.0)
        self.assertEqual(score_pe_valuation(35.0, None), 65.0)
        self.assertEqual(score_pe_valuation(50.0, None), 45.0)
        self.assertEqual(score_pe_valuation(75.0, None), 20.0)

    def test_factor_weights_validation(self):
        weights = FactorWeights()
        weights.validate()  # Valid sum == 1.0

        invalid = FactorWeights(gmp=0.5, qib_subscription=0.8)
        with self.assertRaises(ValueError):
            invalid.validate()


class TestIPORecommendationEngine(unittest.TestCase):
    """Tests the full Recommendation Intelligence Engine workflow."""

    def setUp(self):
        self.engine = IPORecommendationEngine()

    def _create_sample_record(
        self,
        ipo_id="TEST-001",
        gmp_pct=40.0,
        qib_multiple=30.0,
        nii_multiple=15.0,
        retail_multiple=6.0,
        rev_growth=25.0,
        pat_growth=30.0,
        roe=22.0,
        debt_ratio=0.3,
        pe=22.0,
        peer_pe=30.0,
        status=DataCompletenessEnum.COMPLETE,
    ) -> MasterIPORecord:
        raw_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": ipo_id,
                "company_name": "Apex Tech India Ltd",
                "company_legal_name": "Apex Tech India Limited",
                "ticker_symbol": "APEXTECH",
                "isin": "INE123A01010",
                "segment": "Mainboard",
                "sector": "Technology",
                "industry": "Software",
            },
            "ipo_status": {
                "status": "Currently Open",
                "research_date": "2026-10-12",
                "research_time": "10:00:00",
                "data_cutoff": "2026-10-12 09:30:00",
                "open_date": "2026-10-10",
                "close_date": "2026-10-14",
                "listing_date": "2026-10-20",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 500.0, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_amount": {"value": 350.0, "unit": "Crores", "data_type": "Reported"},
                "ofs_amount": {"value": 150.0, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_percentage": {"value": 70.0, "data_type": "Calculated"},
                "ofs_percentage": {"value": 30.0, "data_type": "Calculated"},
                "face_value": {"value": 10.0, "data_type": "Reported"},
                "price_band_low": {"value": 480.0, "data_type": "Reported"},
                "price_band_high": {"value": 500.0, "data_type": "Reported"},
                "issue_price": {"value": 500.0, "data_type": "Reported"},
                "lot_size": {"value": 30, "data_type": "Reported"},
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
                "reference_price": 500.0,
                "reference_eps": 22.7,
                "issue_pe": {"value": pe, "data_type": "Calculated"},
                "peer_average_pe": {"value": peer_pe, "data_type": "Reported"} if peer_pe else None,
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-10-12",
            },
            "scenario_40_percent": {
                "reference_price": 500.0,
                "target_price": 700.0,
                "required_price_movement": 40.0,
                "target_pe": pe * 1.4,
                "supporting_factors": ["High demand"],
                "contradictory_factors": [],
                "scenario_status": "Supported",
                "scenario_methodology": "Standardized",
                "scenario_data_timestamp": "2026-10-12 10:00:00",
            },
            "data_quality": {
                "completeness_status": status.value if hasattr(status, "value") else str(status),
                "source_verification_status": "Verified",
                "last_verified": "2026-10-12 10:00:00",
            },
        }
        rec = JSONIngestor.from_dict(raw_json)
        rec.gmp_data = GMPData(
            gmp_value=200.0,
            gmp_percentage=gmp_pct,
            gmp_date="2026-10-12",
            gmp_time="10:00:00",
            reference_price=500.0,
            implied_price=700.0,
            source="Investorgain",
        )
        rec.subscription_data = {
            "QIB": SubscriptionCategory(
                shares_offered=100000,
                shares_bid=int(100000 * qib_multiple),
                subscription_multiple=qib_multiple,
                source="BSE/NSE",
                source_date="2026-10-12",
                retrieval_timestamp="2026-10-12 17:00:00",
            ),
            "NII": SubscriptionCategory(
                shares_offered=100000,
                shares_bid=int(100000 * nii_multiple),
                subscription_multiple=nii_multiple,
                source="BSE/NSE",
                source_date="2026-10-12",
                retrieval_timestamp="2026-10-12 17:00:00",
            ),
            "Retail": SubscriptionCategory(
                shares_offered=100000,
                shares_bid=int(100000 * retail_multiple),
                subscription_multiple=retail_multiple,
                source="BSE/NSE",
                source_date="2026-10-12",
                retrieval_timestamp="2026-10-12 17:00:00",
            ),
        }
        return rec

    def test_strong_subscribe_evaluation(self):
        record = self._create_sample_record(
            gmp_pct=55.0,
            qib_multiple=60.0,
            nii_multiple=40.0,
            retail_multiple=12.0,
            rev_growth=40.0,
            pat_growth=45.0,
            roe=28.0,
            debt_ratio=0.1,
            pe=18.0,
            peer_pe=32.0,
        )
        res = self.engine.evaluate(record)

        self.assertEqual(res.recommendation, RecommendationCategory.STRONG_SUBSCRIBE)
        self.assertGreaterEqual(res.composite_score, 75.0)
        self.assertEqual(res.risk_level, RiskLevel.LOW)
        self.assertIsNone(res.veto_applied)
        self.assertGreaterEqual(len(res.strengths), 2)
        self.assertEqual(res.confidence_score, 1.0)

    def test_subscribe_evaluation(self):
        record = self._create_sample_record(
            gmp_pct=20.0,
            qib_multiple=8.0,
            nii_multiple=5.0,
            retail_multiple=3.0,
            rev_growth=15.0,
            pat_growth=18.0,
            roe=14.0,
            debt_ratio=0.8,
            pe=28.0,
            peer_pe=32.0,
        )
        res = self.engine.evaluate(record)

        self.assertEqual(res.recommendation, RecommendationCategory.SUBSCRIBE)
        self.assertTrue(60.0 <= res.composite_score < 75.0)
        self.assertIn(res.risk_level, [RiskLevel.LOW, RiskLevel.MEDIUM])

    def test_neutral_evaluation(self):
        record = self._create_sample_record(
            gmp_pct=7.0,
            qib_multiple=2.5,
            nii_multiple=1.5,
            retail_multiple=1.2,
            rev_growth=8.0,
            pat_growth=5.0,
            roe=8.0,
            debt_ratio=1.5,
            pe=35.0,
            peer_pe=32.0,
        )
        res = self.engine.evaluate(record)

        self.assertEqual(res.recommendation, RecommendationCategory.NEUTRAL)
        self.assertTrue(45.0 <= res.composite_score < 60.0)

    def test_avoid_evaluation_low_score(self):
        record = self._create_sample_record(
            gmp_pct=1.0,
            qib_multiple=0.8,
            nii_multiple=0.5,
            retail_multiple=0.6,
            rev_growth=-10.0,
            pat_growth=-15.0,
            roe=2.0,
            debt_ratio=2.8,
            pe=80.0,
            peer_pe=30.0,
        )
        res = self.engine.evaluate(record)

        self.assertEqual(res.recommendation, RecommendationCategory.AVOID)
        self.assertLess(res.composite_score, 45.0)
        self.assertIn(res.risk_level, [RiskLevel.HIGH, RiskLevel.VERY_HIGH])

    def test_veto_rule_negative_gmp_and_qib_undersubscribed(self):
        # Negative GMP + QIB < 1.0x triggers absolute veto
        record = self._create_sample_record(
            gmp_pct=-10.0,
            qib_multiple=0.6,
            rev_growth=25.0,
            pat_growth=25.0,
        )
        res = self.engine.evaluate(record)

        self.assertEqual(res.recommendation, RecommendationCategory.AVOID)
        self.assertIsNotNone(res.veto_applied)
        self.assertIn("Negative GMP", res.veto_applied)
        self.assertEqual(res.risk_level, RiskLevel.VERY_HIGH)
        self.assertIn("CRITICAL RED FLAG VETO", res.summary_rationale)

    def test_veto_rule_high_debt_and_contracting_pat(self):
        record = self._create_sample_record(
            gmp_pct=30.0,
            qib_multiple=15.0,
            debt_ratio=4.2,
            pat_growth=-12.0,
        )
        res = self.engine.evaluate(record)

        self.assertEqual(res.recommendation, RecommendationCategory.AVOID)
        self.assertIsNotNone(res.veto_applied)
        self.assertIn("Excessive debt-to-equity", res.veto_applied)
        self.assertEqual(res.risk_level, RiskLevel.VERY_HIGH)

    def test_missing_data_and_confidence_degradation(self):
        # Sparse record with missing financials and subscriptions
        sparse_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "SPARSE-01",
                "company_name": "Sparse IPO Ltd",
                "company_legal_name": "Sparse IPO Limited",
                "ticker_symbol": "SPARSE",
                "isin": "Not available",
                "segment": "Mainboard",
                "sector": "Other",
                "industry": "Other",
            },
            "ipo_status": {
                "status": "Opening Today",
                "research_date": "2026-10-12",
                "research_time": "10:00:00",
                "data_cutoff": "2026-10-12 09:30:00",
                "open_date": "2026-10-12",
                "close_date": "2026-10-15",
                "listing_date": "2026-10-20",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 100.0, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_amount": {"value": 100.0, "unit": "Crores", "data_type": "Reported"},
                "ofs_amount": {"value": 0.0, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_percentage": {"value": 100.0, "data_type": "Calculated"},
                "ofs_percentage": {"value": 0.0, "data_type": "Calculated"},
                "face_value": {"value": 10.0, "data_type": "Reported"},
                "price_band_low": {"value": 100.0, "data_type": "Reported"},
                "price_band_high": {"value": 100.0, "data_type": "Reported"},
                "issue_price": {"value": 100.0, "data_type": "Reported"},
                "lot_size": {"value": 100, "data_type": "Reported"},
                "minimum_investment": {"value": 10000.0, "data_type": "Calculated"},
            },
            "valuation_data": {
                "reference_price": 100.0,
                "reference_eps": 5.0,
                "issue_pe": {"value": "Not available", "data_type": "Not available"},
                "valuation_method": "None",
                "valuation_source": "None",
                "valuation_date": "2026-10-12",
            },
            "scenario_40_percent": {
                "reference_price": 100.0,
                "target_price": 140.0,
                "required_price_movement": 40.0,
                "target_pe": 28.0,
                "supporting_factors": [],
                "contradictory_factors": [],
                "scenario_status": "Insufficient evidence",
                "scenario_methodology": "Standardized",
                "scenario_data_timestamp": "2026-10-12 10:00:00",
            },
            "data_quality": {
                "completeness_status": "Insufficient evidence",
                "source_verification_status": "Not verified",
                "last_verified": "2026-10-12 10:00:00",
            },
        }
        sparse_rec = JSONIngestor.from_dict(sparse_json)
        res = self.engine.evaluate(sparse_rec)

        self.assertIsInstance(res, RecommendationResult)
        self.assertLessEqual(res.confidence_score, 0.5)
        # Neutral fallbacks yield 40-50 composite score
        self.assertGreaterEqual(res.composite_score, 40.0)

    def test_gmp_override_and_batch_evaluation(self):
        rec1 = self._create_sample_record("IPO-1", gmp_pct=10.0)
        rec2 = self._create_sample_record("IPO-2", gmp_pct=45.0)

        results = self.engine.evaluate_batch([rec1, rec2])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].ipo_id, "IPO-1")
        self.assertEqual(results[1].ipo_id, "IPO-2")

        # Test single override
        override_gmp = GMPData(
            gmp_value=400.0,
            gmp_percentage=80.0,
            gmp_date="2026-10-12",
            gmp_time="10:00:00",
            reference_price=500.0,
            implied_price=900.0,
            source="ManualOverride",
        )
        res_override = self.engine.evaluate(rec1, gmp_override=override_gmp)
        self.assertEqual(res_override.factor_scores["gmp"].raw_value, 80.0)
        self.assertEqual(res_override.factor_scores["gmp"].normalized_score, 100.0)

    def test_to_dict_serialization(self):
        record = self._create_sample_record()
        res = self.engine.evaluate(record)
        res_dict = res.to_dict()

        self.assertEqual(res_dict["ipo_id"], "TEST-001")
        self.assertIn("recommendation", res_dict)
        self.assertIn("composite_score", res_dict)
        self.assertIn("factor_scores", res_dict)
        self.assertIn("gmp", res_dict["factor_scores"])
        self.assertIn("pe_valuation", res_dict["factor_scores"])
        self.assertEqual(len(res_dict["factor_scores"]), 9)


if __name__ == "__main__":
    unittest.main()
