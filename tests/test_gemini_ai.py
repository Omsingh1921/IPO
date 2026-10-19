"""
Unit and integration tests for Google Gemini AI Service and API Endpoints.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from ipo_platform.api.app import create_app
from ipo_platform.api.dependencies import set_db_engine
from ipo_platform.db.session import get_engine, init_db
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.security import Role, create_access_token
from ipo_platform.services.gemini_service import GeminiService
from ipo_platform.services.ingestion_service import IPOIngestionService


class TestGeminiAISuite(unittest.TestCase):
    """Test suite validating GeminiService and AI routes."""

    @classmethod
    def setUpClass(cls):
        cls.engine = get_engine("sqlite:///:memory:")
        init_db(cls.engine)
        set_db_engine(cls.engine)

        cls.app = create_app()
        cls.client = TestClient(cls.app)

        cls.readonly_token = create_access_token(principal_id="test-readonly", role=Role.READ_ONLY)
        cls.operator_token = create_access_token(principal_id="test-operator", role=Role.OPERATOR)

        # Seed sample IPO record conforming to Schema v1.0
        cls.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "NSE-GEMINI-TEST-2026",
                "company_name": "Gemini AI Technologies Limited",
                "company_legal_name": "Gemini AI Technologies Private Limited",
                "ticker_symbol": "GEMINI",
                "isin": "INE005G01015",
                "segment": "Mainboard",
                "sector": "Information Technology",
                "industry": "Artificial Intelligence",
            },
            "ipo_status": {
                "status": "Upcoming",
                "research_date": "2026-10-12",
                "research_time": "10:00:00",
                "data_cutoff": "2026-10-12 10:00:00",
                "open_date": "2026-10-25",
                "close_date": "2026-10-28",
                "allotment_date": "2026-10-29",
                "listing_date": "2026-10-31",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 500.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 350.0, "unit": "Crores"},
                "ofs_amount": {"value": 150.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 70.0},
                "ofs_percentage": {"value": 30.0},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 300.0},
                "price_band_high": {"value": 320.0},
                "issue_price": {"value": 320.0},
                "lot_size": {"value": 45},
                "minimum_investment": {"value": 14400.0},
            },
            "valuation_data": {
                "reference_price": 320.0,
                "reference_eps": 16.0,
                "issue_pe": {"value": 20.0},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-10-12",
            },
            "scenario_40_percent": {
                "reference_price": 320.0,
                "target_price": 448.0,
                "required_price_movement": 40.0,
                "target_pe": 28.0,
                "supporting_factors": ["High AI platform growth"],
                "contradictory_factors": [],
                "scenario_status": "Supported",
                "scenario_methodology": "Standardized non-predictive model",
                "scenario_data_timestamp": "2026-10-12 10:00:00",
            },
            "data_quality": {
                "completeness_status": "Complete",
                "source_verification_status": "Verified",
                "last_verified": "2026-10-12 10:00:00",
            },
        }
        ingestion = IPOIngestionService(cls.engine)
        ingestion.ingest_json_dict(cls.sample_json)

    def test_ai_status_endpoint(self):
        """Validates /ai/status route returns configuration information."""
        resp = self.client.get("/ai/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("configured", data)
        self.assertEqual(data["provider"], "Google Gemini")
        self.assertIn("model", data)

    def test_gemini_service_fallback_thesis(self):
        """Validates algorithmic fallback when API key is missing."""
        service = GeminiService(api_key="")
        self.assertFalse(service.is_configured)

        record = JSONIngestor.from_dict(self.sample_json)
        thesis = service.generate_ipo_thesis(record)

        self.assertIn("verdict", thesis)
        self.assertIn("one_line_verdict", thesis)
        self.assertIn("bull_case", thesis)
        self.assertIn("bear_case", thesis)
        self.assertIn("listing_day_strategy", thesis)
        self.assertTrue(thesis["is_fallback"])

    def test_gemini_service_fallback_copilot(self):
        """Validates copilot fallback answering mechanism."""
        service = GeminiService(api_key="")
        record = JSONIngestor.from_dict(self.sample_json)

        ans = service.ask_ipo_copilot(record, "Should I apply for listing gain?")
        self.assertIn("Listing Gain Analysis", ans)

    @patch("requests.post")
    def test_gemini_live_api_call_success(self, mock_post):
        """Validates live Gemini API parsing when response is returned."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '{"verdict": "STRONG APPLY", "one_line_verdict": "Outstanding growth and robust moats.", "confidence_percentage": 92, "listing_day_strategy": "Hold with trailing stop.", "long_term_outlook": "High conviction.", "bull_case": ["Strong PAT"], "bear_case": ["Valuation high"], "retail_advice": "Apply 1 lot.", "hni_advice": "Apply via bNII."}'
                    }]
                }
            }]
        }
        mock_post.return_value = mock_resp

        service = GeminiService(api_key="dummy-gemini-test-key-123456789")
        self.assertTrue(service.is_configured)

        record = JSONIngestor.from_dict(self.sample_json)
        thesis = service.generate_ipo_thesis(record)

        self.assertEqual(thesis["verdict"], "STRONG APPLY")
        self.assertEqual(thesis["confidence_percentage"], 92)
        self.assertFalse(thesis["is_fallback"])
        self.assertIn("Google Gemini", thesis["ai_provider"])

    def test_api_thesis_endpoint(self):
        """Validates GET /ipos/{id}/ai-thesis API endpoint."""
        headers = {"Authorization": f"Bearer {self.readonly_token}"}
        resp = self.client.get("/ipos/NSE-GEMINI-TEST-2026/ai-thesis", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("verdict", data)
        self.assertIn("bull_case", data)
        self.assertIn("bear_case", data)
        self.assertEqual(data["ipo_id"], "NSE-GEMINI-TEST-2026")

    def test_api_ask_copilot_endpoint(self):
        """Validates POST /ipos/{id}/ai-ask API endpoint."""
        headers = {"Authorization": f"Bearer {self.readonly_token}"}
        payload = {"question": "What is the best strategy for retail category?"}
        resp = self.client.post("/ipos/NSE-GEMINI-TEST-2026/ai-ask", json=payload, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertEqual(data["ipo_id"], "NSE-GEMINI-TEST-2026")
        self.assertEqual(data["question"], payload["question"])


if __name__ == "__main__":
    unittest.main()
