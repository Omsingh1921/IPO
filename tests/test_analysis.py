import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ipo_platform.io.json_ingestor import JSONIngestor
from src.ipo_platform.analysis.reader import IPODataReader
from src.ipo_platform.analysis.valuation_normalizer import ValuationNormalizer
from src.ipo_platform.analysis.growth_analytics import GrowthAnalytics
from src.ipo_platform.analysis.subscription_momentum import SubscriptionMomentumEngine
from src.ipo_platform.analysis.dataset_normalizer import DatasetNormalizer
from src.ipo_platform.models.schema import PeerCompany, ProvenanceEnvelope
from src.ipo_platform.models.enums import DataTypeEnum


class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "IND-MB-2026-MONEYVIEW",
                "company_name": "Moneyview Limited",
                "company_legal_name": "Whizdm Innovations Private Limited",
                "ticker_symbol": "MONEYVIEW",
                "isin": "Not available",
                "segment": "Mainboard",
                "sector": "Fintech / Financial Services",
                "industry": "Digital Lending Platforms",
            },
            "ipo_status": {
                "status": "Opening Today",
                "research_date": "2026-09-24",
                "research_time": "11:15:00",
                "data_cutoff": "2026-09-24 10:45:00",
                "open_date": "2026-09-24",
                "close_date": "2026-09-28",
                "listing_date": "2026-10-01",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 1091.68, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_amount": {"value": 750.00, "unit": "Crores", "data_type": "Reported"},
                "ofs_amount": {"value": 341.68, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_percentage": {"value": 68.70, "data_type": "Calculated"},
                "ofs_percentage": {"value": 31.30, "data_type": "Calculated"},
                "face_value": {"value": 1.00, "data_type": "Reported"},
                "price_band_low": {"value": 32.00, "data_type": "Reported"},
                "price_band_high": {"value": 34.00, "data_type": "Reported"},
                "issue_price": {"value": "Not available", "data_type": "Not available"},
                "lot_size": {"value": 441, "data_type": "Reported"},
                "minimum_investment": {"value": 14994.00, "data_type": "Calculated"},
            },
            "financial_data": [
                {
                    "financial_period": "FY2025",
                    "period_type": "FY",
                    "revenue": {"value": 2378.53, "data_type": "Reported"},
                    "PAT": {"value": 240.28, "data_type": "Reported"},
                    "EBITDA": {"value": 697.98, "data_type": "Reported"},
                },
                {
                    "financial_period": "FY2026",
                    "period_type": "FY",
                    "revenue": {"value": 3404.27, "data_type": "Reported"},
                    "PAT": {"value": 242.71, "data_type": "Reported"},
                    "EBITDA": {"value": 968.92, "data_type": "Reported"},
                },
            ],
            "valuation_data": {
                "reference_price": 34.00,
                "reference_eps": 0.79,
                "issue_pe": {"value": 43.04, "data_type": "Calculated"},
                "industry_pe": {"value": 28.50, "data_type": "Reported"},
                "valuation_method": "Trailing Diluted P/E on FY26 Earnings",
                "valuation_source": "RHP Financial Statements",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 34.00,
                "target_price": 47.60,
                "required_price_movement": 40.00,
                "target_pe": 60.25,
                "supporting_factors": ["GMP quote"],
                "contradictory_factors": ["FY26 PAT growth"],
                "scenario_status": "Insufficient evidence",
                "scenario_methodology": "Standardized non-predictive model",
                "scenario_data_timestamp": "2026-09-24 11:00:00",
            },
            "data_quality": {
                "completeness_status": "Partial",
                "source_verification_status": "Verified",
                "last_verified": "2026-09-24 10:45:00",
            },
        }
        self.record = JSONIngestor.from_dict(self.sample_json)

    def test_raw_data_immutability(self):
        reader = IPODataReader(self.record)
        orig_price = reader.raw_record.issue_structure.price_band_high.value
        self.assertEqual(orig_price, 34.00)

        # Mutate the copy returned by raw_record
        reader.raw_record.issue_structure.price_band_high.value = 999.00

        # Verify underlying stored copy remains untouched
        self.assertEqual(reader.raw_record.issue_structure.price_band_high.value, 34.00)

    def test_valuation_normalizer(self):
        peer1 = PeerCompany(company_name="Peer A", ticker="PEERA", source="RHP", source_date="2026", PE=20.0)
        peer2 = PeerCompany(company_name="Peer B", ticker="PEERB", source="RHP", source_date="2026", PE=30.0)
        self.record.peer_companies = [peer1, peer2]

        analytics = ValuationNormalizer.analyze_valuation(self.record)
        self.assertEqual(analytics["issue_pe"], 43.04)
        self.assertEqual(analytics["peer_median_pe"], 25.0)
        self.assertAlmostEqual(analytics["valuation_spread_vs_peers_percent"], 72.16, places=2)

    def test_growth_analytics(self):
        analytics = GrowthAnalytics.analyze_financials(self.record)
        self.assertEqual(analytics["periods_count"], 2)
        fin26 = analytics["financial_periods"][1]
        self.assertAlmostEqual(fin26["revenue_growth_yoy_percent"], 43.12, places=2)
        self.assertAlmostEqual(fin26["ebitda_margin_percent"], 28.46, places=2)
        self.assertAlmostEqual(analytics["revenue_cagr_percent"], 43.12, places=2)

    def test_dataset_normalizer(self):
        normalized = DatasetNormalizer.generate_normalized_dataset(self.record)
        self.assertEqual(normalized["ipo_id"], "IND-MB-2026-MONEYVIEW")
        self.assertIn("growth_analytics", normalized)
        self.assertIn("valuation_analytics", normalized)

        # Verify file output saving
        output_path = DatasetNormalizer.save_normalized_dataset(self.record, output_dir="data/processed")
        self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main()
