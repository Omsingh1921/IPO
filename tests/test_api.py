"""
Integration Test Suite for Indian IPO REST API Platform (Phase 10 - Stage 4).
Validates:
- GET /health
- GET /ipos and GET /ipos/{ipo_id}
- POST /recommendation/evaluate
- POST /recommendation/validate
- POST /portfolio/allocate
- GET /metrics
- OpenAPI schema and route definitions
- Dependency injection overrides
- Global exception handling and input validation
"""

import os
import sys
import unittest

# Ensure src is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient

from ipo_platform.api.app import create_app
from ipo_platform.api.dependencies import (
    get_db_engine,
    get_query_service,
    set_db_engine,
)
from ipo_platform.db.base import Base
from ipo_platform.db.repository import IPOWriteRepository
from ipo_platform.db.session import get_db_session, get_engine
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.schema import MasterIPORecord


def create_sample_master_record(
    ipo_id="API-TEST-001",
    company_name="Test Apex Technologies Ltd",
    gmp_pct=35.0,
    is_historical=False,
    listing_day_return=38.0,
) -> dict:
    """Helper generating canonical MasterIPORecord JSON payload."""
    data = {
        "schema_version": "1.0",
        "ipo_entity": {
            "ipo_id": ipo_id,
            "company_name": company_name,
            "company_legal_name": f"{company_name} Limited",
            "ticker_symbol": "TESTAPEX",
            "isin": "INE999A01019",
            "segment": "Mainboard",
            "sector": "Technology",
            "industry": "Software Solutions",
        },
        "ipo_status": {
            "status": "Listed" if is_historical else "Currently Open",
            "research_date": "2026-10-12",
            "research_time": "10:00:00",
            "data_cutoff": "2026-10-12 09:30:00",
            "open_date": "2026-10-10",
            "close_date": "2026-10-14",
            "listing_date": "2026-10-20",
            "listing_status": "Listed" if is_historical else "Pre-Listing",
        },
        "issue_structure": {
            "issue_size": {"value": 600.0, "unit": "Crores", "data_type": "Reported"},
            "fresh_issue_amount": {"value": 450.0, "unit": "Crores", "data_type": "Reported"},
            "ofs_amount": {"value": 150.0, "unit": "Crores", "data_type": "Reported"},
            "fresh_issue_percentage": {"value": 75.0, "data_type": "Calculated"},
            "ofs_percentage": {"value": 25.0, "data_type": "Calculated"},
            "face_value": {"value": 10.0, "data_type": "Reported"},
            "price_band_low": {"value": 475.0, "data_type": "Reported"},
            "price_band_high": {"value": 500.0, "data_type": "Reported"},
            "issue_price": {"value": 500.0, "data_type": "Reported"},
            "lot_size": {"value": 30, "data_type": "Reported"},
            "minimum_investment": {"value": 15000.0, "data_type": "Calculated"},
        },
        "financial_data": [
            {
                "financial_period": "FY24",
                "period_type": "FY",
                "revenue_growth": {"value": 28.5, "data_type": "Calculated"},
                "PAT_growth": {"value": 32.0, "data_type": "Calculated"},
                "ROE": {"value": 24.0, "data_type": "Calculated"},
                "debt_equity": {"value": 0.25, "data_type": "Calculated"},
            }
        ],
        "valuation_data": {
            "reference_price": 500.0,
            "reference_eps": 25.0,
            "issue_pe": {"value": 20.0, "data_type": "Calculated"},
            "peer_average_pe": {"value": 28.0, "data_type": "Reported"},
            "valuation_method": "Relative PE",
            "valuation_source": "RHP",
            "valuation_date": "2026-10-12",
        },
        "scenario_40_percent": {
            "reference_price": 500.0,
            "target_price": 700.0,
            "required_price_movement": 40.0,
            "target_pe": 28.0,
            "supporting_factors": ["High demand", "Robust margins"],
            "contradictory_factors": [],
            "scenario_status": "Supported",
            "scenario_methodology": "Standardized",
            "scenario_data_timestamp": "2026-10-12 10:00:00",
        },
        "data_quality": {
            "completeness_status": "Complete",
            "source_verification_status": "Verified",
            "last_verified": "2026-10-12 10:00:00",
        },
        "gmp_data": {
            "gmp_value": 175.0,
            "gmp_percentage": gmp_pct,
            "gmp_date": "2026-10-12",
            "gmp_time": "10:00:00",
            "reference_price": 500.0,
            "implied_price": 675.0,
            "source": "Investorgain",
        },
        "subscription_data": {
            "QIB": {
                "shares_offered": 100000,
                "shares_applied": 3500000,
                "subscription_multiple": 35.0,
                "data_type": "Reported",
                "source": "NSE",
            },
            "NII": {
                "shares_offered": 100000,
                "shares_applied": 1800000,
                "subscription_multiple": 18.0,
                "data_type": "Reported",
                "source": "NSE",
            },
            "Retail": {
                "shares_offered": 100000,
                "shares_applied": 850000,
                "subscription_multiple": 8.5,
                "data_type": "Reported",
                "source": "NSE",
            },
        },
    }
    if is_historical:
        data["historical_ipo"] = {
            "historical_ipo": True,
            "ipo_year": 2024,
            "listing_price": 680.0,
            "listing_day_close": 690.0,
            "listing_day_return": listing_day_return,
            "post_listing_30d_return": 42.0,
            "max_upside_from_issue_price": 50.0,
            "max_drawdown_from_issue_price": -2.0,
        }
    return data


class TestIPOPlatformAPI(unittest.TestCase):
    """Integration test suite covering all REST endpoints of the platform."""

    @classmethod
    def setUpClass(cls):
        # Configure isolated in-memory test database
        cls.test_engine = get_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.test_engine)
        set_db_engine(cls.test_engine)

        from ipo_platform.security import Role, create_access_token
        admin_token = create_access_token(principal_id="test-admin", role=Role.ADMIN)
        cls.app = create_app()
        cls.client = TestClient(cls.app, headers={"Authorization": f"Bearer {admin_token}"})

        # Seed sample record in the test database
        sample_dict = create_sample_master_record("SEED-IPO-001", "Seed Tech Industries Ltd", 45.0)
        record = JSONIngestor.from_dict(sample_dict)
        with get_db_session(cls.test_engine) as session:
            IPOWriteRepository.save_master_record(session, record)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.test_engine)
        set_db_engine(None)

    # -------------------------------------------------------------
    # 1. Health Probe Endpoint: GET /health
    # -------------------------------------------------------------
    def test_get_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("status", data)
        self.assertIn("healthy_count", data)
        self.assertIn("checks", data)
        self.assertIn("database", data["checks"])
        self.assertIn("redis", data["checks"])
        self.assertIn("notifications", data["checks"])
        self.assertEqual(data["checks"]["database"]["status"], "HEALTHY")

    # -------------------------------------------------------------
    # 2. IPO Catalog Endpoints: GET /ipos and GET /ipos/{ipo_id}
    # -------------------------------------------------------------
    def test_list_ipos(self):
        response = self.client.get("/ipos")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertGreaterEqual(data["total"], 1)

        first_item = data["items"][0]
        self.assertEqual(first_item["ipo_id"], "SEED-IPO-001")
        self.assertEqual(first_item["company_name"], "Seed Tech Industries Ltd")
        self.assertEqual(first_item["sector"], "Technology")
        self.assertEqual(first_item["issue_size_cr"], 600.0)

    def test_list_ipos_with_filter(self):
        # Filter by status
        response = self.client.get("/ipos?status=Currently+Open")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data["total"], 1)

        # Filter by sector
        response_sector = self.client.get("/ipos?sector=Technology")
        self.assertEqual(response_sector.status_code, 200)
        self.assertGreaterEqual(response_sector.json()["total"], 1)

        # Filter non-existent sector
        response_empty = self.client.get("/ipos?sector=NonExistentSector")
        self.assertEqual(response_empty.status_code, 200)
        self.assertEqual(response_empty.json()["total"], 0)

    def test_get_ipo_by_id_success(self):
        response = self.client.get("/ipos/SEED-IPO-001")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["ipo_id"], "SEED-IPO-001")
        self.assertEqual(data["company_name"], "Seed Tech Industries Ltd")
        self.assertIn("record", data)
        self.assertEqual(data["record"]["ipo_entity"]["ticker_symbol"], "TESTAPEX")

    def test_get_ipo_by_id_not_found(self):
        response = self.client.get("/ipos/UNKNOWN-IPO-999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "HTTP_EXCEPTION")
        self.assertIn("not found", data["detail"])

    # -------------------------------------------------------------
    # 3. Recommendation Evaluation: POST /recommendation/evaluate
    # -------------------------------------------------------------
    def test_evaluate_recommendation_from_record(self):
        payload_record = create_sample_master_record("EVAL-001", "Evaluated Growth Ltd", 45.0)
        body = {"record": payload_record}

        response = self.client.post("/recommendation/evaluate", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["ipo_id"], "EVAL-001")
        self.assertIn(data["recommendation"], ["SUBSCRIBE", "STRONG_SUBSCRIBE"])
        self.assertGreater(data["composite_score"], 60.0)
        self.assertIn("factor_scores", data)
        self.assertEqual(len(data["factor_scores"]), 9)
        self.assertIn("gmp", data["factor_scores"])
        self.assertIn("qib_subscription", data["factor_scores"])
        self.assertIn("summary_rationale", data)

    def test_evaluate_recommendation_with_gmp_override(self):
        payload_record = create_sample_master_record("EVAL-002", "Override Pharma Ltd", 10.0)
        body = {
            "record": payload_record,
            "gmp_override": {
                "gmp_value": 350.0,
                "gmp_percentage": 70.0,
                "reference_price": 500.0,
                "source": "Custom Analyst Override",
            },
        }

        response = self.client.post("/recommendation/evaluate", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["factor_scores"]["gmp"]["raw_value"], 70.0)
        self.assertEqual(data["factor_scores"]["gmp"]["score"], 100.0)

    def test_evaluate_recommendation_by_ipo_id(self):
        body = {"ipo_id": "SEED-IPO-001"}
        response = self.client.post("/recommendation/evaluate", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ipo_id"], "SEED-IPO-001")
        self.assertIn("recommendation", data)

    def test_evaluate_recommendation_missing_inputs(self):
        # Neither record nor ipo_id provided
        response = self.client.post("/recommendation/evaluate", json={})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "HTTP_EXCEPTION")

    def test_evaluate_recommendation_ipo_id_not_found(self):
        body = {"ipo_id": "NON-EXISTENT-IPO"}
        response = self.client.post("/recommendation/evaluate", json=body)
        self.assertEqual(response.status_code, 404)

    # -------------------------------------------------------------
    # 4. Recommendation Validation: POST /recommendation/validate
    # -------------------------------------------------------------
    def test_validate_recommendations(self):
        rec1 = create_sample_master_record("HIST-001", "Hist One Ltd", 50.0, is_historical=True, listing_day_return=45.0)
        rec2 = create_sample_master_record("HIST-002", "Hist Two Ltd", -10.0, is_historical=True, listing_day_return=-8.0)

        body = {
            "records": [rec1, rec2],
            "strong_subscribe_success_min_return": 15.0,
            "subscribe_success_min_return": 5.0,
            "avoid_success_max_return": 5.0,
        }

        response = self.client.post("/recommendation/validate", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_evaluated"], 2)
        self.assertEqual(data["historical_cohort_size"], 2)
        self.assertIn("overall_accuracy", data)
        self.assertIn("category_breakdown", data)
        self.assertIn("STRONG_SUBSCRIBE", data["category_breakdown"])
        self.assertIn("AVOID", data["category_breakdown"])

    # -------------------------------------------------------------
    # 5. Portfolio Allocation: POST /portfolio/allocate
    # -------------------------------------------------------------
    def test_allocate_portfolio_from_recommendations(self):
        body = {
            "available_capital": 500000.0,
            "risk_profile": "MODERATE",
            "recommendations": [
                {
                    "ipo_id": "IPO-A",
                    "company_name": "Alpha Tech",
                    "recommendation": "STRONG_SUBSCRIBE",
                    "composite_score": 88.0,
                    "confidence_score": 0.9,
                    "risk_level": "LOW",
                    "sector": "Technology",
                },
                {
                    "ipo_id": "IPO-B",
                    "company_name": "Beta Healthcare",
                    "recommendation": "SUBSCRIBE",
                    "composite_score": 72.0,
                    "confidence_score": 0.85,
                    "risk_level": "MEDIUM",
                    "sector": "Healthcare",
                },
                {
                    "ipo_id": "IPO-C",
                    "company_name": "Gamma Metals",
                    "recommendation": "AVOID",
                    "composite_score": 30.0,
                    "confidence_score": 0.7,
                    "risk_level": "VERY_HIGH",
                    "sector": "Metals",
                },
            ],
        }

        response = self.client.post("/portfolio/allocate", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_capital"], 500000.0)
        self.assertGreater(data["total_allocated_capital"], 0.0)
        self.assertLessEqual(data["total_allocated_capital"], 500000.0)
        self.assertGreaterEqual(data["unallocated_cash"], 0.0)
        self.assertEqual(data["risk_profile"], "MODERATE")

        # Verify AVOID receives 0
        allocations = {a["ipo_id"]: a for a in data["allocations"]}
        self.assertEqual(allocations["IPO-C"]["allocated_amount"], 0.0)

        # Single IPO cap check: <= 35%
        for alloc in data["allocations"]:
            self.assertLessEqual(alloc["allocation_percentage"], 35.01)

        # Verify sector allocations
        self.assertIn("Technology", data["sector_allocations"])
        self.assertIn("Healthcare", data["sector_allocations"])

        # Risk metrics
        self.assertGreater(data["portfolio_risk_score"], 0.0)
        self.assertIn("expected_return", data)
        self.assertIn("sharpe_score", data)

    def test_allocate_portfolio_validation_errors(self):
        # Negative capital
        body = {
            "available_capital": -1000.0,
            "risk_profile": "MODERATE",
        }
        response = self.client.post("/portfolio/allocate", json=body)
        self.assertEqual(response.status_code, 422)

        # Zero capital
        body_zero = {
            "available_capital": 0.0,
            "risk_profile": "MODERATE",
        }
        response_zero = self.client.post("/portfolio/allocate", json=body_zero)
        self.assertEqual(response_zero.status_code, 422)

        # Invalid risk profile enum
        body_invalid_enum = {
            "available_capital": 100000.0,
            "risk_profile": "ULTRA_RISKY",
        }
        response_enum = self.client.post("/portfolio/allocate", json=body_invalid_enum)
        self.assertEqual(response_enum.status_code, 422)

    # -------------------------------------------------------------
    # 6. Observability Metrics Endpoint: GET /metrics
    # -------------------------------------------------------------
    def test_get_metrics(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("timestamp", data)
        self.assertIn("counters", data)
        self.assertIn("gauges", data)
        self.assertIn("timers", data)

        # Verify timing header is attached by telemetry middleware
        self.assertIn("x-process-time", response.headers)

    # -------------------------------------------------------------
    # 7. OpenAPI Specifications: GET /openapi.json and GET /docs
    # -------------------------------------------------------------
    def test_openapi_schema(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        self.assertEqual(schema["info"]["title"], "Indian IPO Recommendation Platform API")
        self.assertEqual(schema["info"]["version"], "1.0.0")

        # Verify required endpoints are all registered
        paths = schema["paths"]
        self.assertIn("/health", paths)
        self.assertIn("/ipos", paths)
        self.assertIn("/ipos/{ipo_id}", paths)
        self.assertIn("/recommendation/evaluate", paths)
        self.assertIn("/recommendation/validate", paths)
        self.assertIn("/portfolio/allocate", paths)
        self.assertIn("/metrics", paths)

    def test_swagger_and_redoc_ui(self):
        resp_docs = self.client.get("/docs")
        self.assertEqual(resp_docs.status_code, 200)
        self.assertIn(b"swagger-ui", resp_docs.content.lower())

        resp_redoc = self.client.get("/redoc")
        self.assertEqual(resp_redoc.status_code, 200)
        self.assertIn(b"redoc", resp_redoc.content.lower())


if __name__ == "__main__":
    unittest.main()
