"""
End-to-End Integration and Product Readiness Test Suite (Phase 10 - Stage 6).
Validates complete user journeys and architectural integrity across 12 required scenarios:

Scenario A: IPO listing -> IPO details -> recommendation evaluation workflow.
Scenario B: Recommendation evaluation -> recommendation validation workflow.
Scenario C: Portfolio input -> allocation response -> mathematical invariants.
Scenario D: Unauthenticated request -> correct 401 rejection across all protected endpoints.
Scenario E: Authenticated READ_ONLY user -> permitted read access and denied privileged operations (403).
Scenario F: Invalid, missing, or malformed inputs -> controlled errors (400/422) without internal leakage.
Scenario G: Empty IPO dataset and missing records -> documented behavior without fabricated results.
Scenario H: Redis outage -> verify configured fail-open (standard) and fail-closed (expensive) behavior.
Scenario I: Token integrity -> expired token, tampered token, revoked token rejection.
Scenario J: Portfolio allocation regression checks (duplicate IPO caps, rounding, exposure caps, all-AVOID).
Scenario K: Health check probe -> verifies clean diagnostic summary without leaking internal credentials/URLs.
Scenario L: Observability metrics & logs -> verifies performance metrics without credential or token leakage.
Scenario M: Web Dashboard interface -> verifies native SPA delivery and CSP compliance.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient
import jwt

from ipo_platform.api.app import create_app
from ipo_platform.api.dependencies import set_db_engine
from ipo_platform.db.base import Base
from ipo_platform.db.repository import IPOWriteRepository
from ipo_platform.db.session import get_db_session, get_engine
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.security.auth import (
    AuthenticatedPrincipal,
    create_access_token,
    get_revocation_store,
    set_revocation_store,
)
from ipo_platform.security.config import SecurityConfig, set_security_config
from ipo_platform.security.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    set_rate_limiter,
)
from ipo_platform.security.rbac import Role
from tests.test_api import create_sample_master_record


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests verifying complete platform workflows."""

    @classmethod
    def setUpClass(cls):
        # Configure isolated in-memory SQLite database
        cls.test_engine = get_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.test_engine)
        set_db_engine(cls.test_engine)

        cls.jwt_secret = "test-secret-e2e-integration-32-chars-long-12345!"
        cls.api_keys = {
            "key-reader-e2e": "READ_ONLY",
            "key-operator-e2e": "OPERATOR",
            "key-admin-e2e": "ADMIN",
        }

        cls.config = SecurityConfig(
            environment="test",
            auth_enabled=True,
            jwt_secret=cls.jwt_secret,
            jwt_algorithm="HS256",
            jwt_issuer="ipo-platform-test",
            jwt_audience="ipo-api-test",
            api_keys=cls.api_keys,
            cors_allowed_origins=["*"],
            cors_allow_credentials=True,
            trusted_hosts=["testserver", "localhost", "127.0.0.1"],
            rate_limit_enabled=True,
            rate_limit_unauthenticated_rpm=60,
            rate_limit_authenticated_rpm=200,
            rate_limit_expensive_rpm=30,
            rate_limit_fail_closed_expensive=True,
            max_request_body_bytes=1024 * 1024,
            docs_enabled=True,
        )
        set_security_config(cls.config)
        set_rate_limiter(InMemoryRateLimiter())

        cls.app = create_app(config=cls.config)
        cls.client = TestClient(cls.app)

        # Generate tokens for each role
        cls.reader_token = create_access_token("e2e-reader", Role.READ_ONLY, config=cls.config)
        cls.operator_token = create_access_token("e2e-operator", Role.OPERATOR, config=cls.config)
        cls.admin_token = create_access_token("e2e-admin", Role.ADMIN, config=cls.config)

        # Seed sample IPO record in test database
        cls.seed_ipo_id = "TECH-E2E-001"
        cls.seed_company = "Nexus Cloud Technologies Ltd"
        cls.sample_record_dict = create_sample_master_record(
            ipo_id=cls.seed_ipo_id,
            company_name=cls.seed_company,
            gmp_pct=42.0,
            is_historical=False,
        )
        parsed_record = JSONIngestor.from_dict(cls.sample_record_dict)
        with get_db_session(cls.test_engine) as session:
            IPOWriteRepository.save_master_record(session, parsed_record)

    def setUp(self):
        set_rate_limiter(InMemoryRateLimiter())

    # =========================================================================
    # Scenario A: IPO Listing -> IPO Details -> Recommendation Evaluation
    # =========================================================================
    def test_scenario_a_listing_to_details_to_evaluate(self):
        """Trace: Authenticated user lists IPOs, opens specific IPO, and runs recommendation evaluation."""
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        # Step 1: List IPOs
        list_resp = self.client.get("/ipos", headers=headers)
        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.json()
        self.assertIn("items", list_data)
        ipos = list_data["items"]
        self.assertIsInstance(ipos, list)
        self.assertGreaterEqual(len(ipos), 1)

        target_ipo = next((i for i in ipos if i["ipo_id"] == self.seed_ipo_id), None)
        self.assertIsNotNone(target_ipo)
        self.assertEqual(target_ipo["company_name"], self.seed_company)
        self.assertEqual(target_ipo["status"], "Currently Open")

        # Step 2: Fetch detailed record by ID
        detail_resp = self.client.get(f"/ipos/{self.seed_ipo_id}", headers=headers)
        self.assertEqual(detail_resp.status_code, 200)
        detail_data = detail_resp.json()
        self.assertEqual(detail_data["ipo_id"], self.seed_ipo_id)
        self.assertIn("record", detail_data)
        record = detail_data["record"]
        self.assertEqual(record["ipo_entity"]["company_name"], self.seed_company)

        # Step 3: Run recommendation evaluation using retrieved record
        eval_resp = self.client.post("/recommendation/evaluate", json={"record": record}, headers=headers)
        self.assertEqual(eval_resp.status_code, 200)
        eval_data = eval_resp.json()

        self.assertEqual(eval_data["ipo_id"], self.seed_ipo_id)
        self.assertIn(eval_data["recommendation"], ["STRONG_SUBSCRIBE", "SUBSCRIBE", "NEUTRAL", "AVOID"])
        self.assertGreaterEqual(eval_data["composite_score"], 0.0)
        self.assertLessEqual(eval_data["composite_score"], 100.0)
        self.assertIn("factor_scores", eval_data)
        self.assertEqual(len(eval_data["factor_scores"]), 9)
        self.assertIn("summary_rationale", eval_data)
        self.assertIn("strengths", eval_data)
        self.assertIn("risks", eval_data)

    # =========================================================================
    # Scenario B: Recommendation Evaluation -> Recommendation Validation
    # =========================================================================
    def test_scenario_b_evaluation_to_validation(self):
        """Trace: Evaluate historical IPOs and validate predictions against actual listing performance."""
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        # Create two historical cohorts: one successful, one underperforming
        hist_winner = create_sample_master_record(
            "HIST-WIN-01", "Winner Technologies Ltd", 50.0, is_historical=True, listing_day_return=48.0
        )
        hist_loser = create_sample_master_record(
            "HIST-LOSE-01", "Overvalued Infra Ltd", -15.0, is_historical=True, listing_day_return=-12.0
        )

        # Submit validation cohort
        validate_body = {
            "records": [hist_winner, hist_loser],
            "strong_subscribe_success_min_return": 15.0,
            "subscribe_success_min_return": 5.0,
            "avoid_success_max_return": 5.0,
        }
        val_resp = self.client.post("/recommendation/validate", json=validate_body, headers=headers)
        self.assertEqual(val_resp.status_code, 200)
        val_data = val_resp.json()

        self.assertEqual(val_data["total_evaluated"], 2)
        self.assertEqual(val_data["historical_cohort_size"], 2)
        self.assertIn("overall_accuracy", val_data)
        self.assertGreaterEqual(val_data["overall_accuracy"], 0.0)
        self.assertLessEqual(val_data["overall_accuracy"], 100.0)
        self.assertIn("category_breakdown", val_data)

    # =========================================================================
    # Scenario C: Valid Portfolio Input -> Allocation Response -> Invariants
    # =========================================================================
    def test_scenario_c_portfolio_allocation_and_invariants(self):
        """Trace: Submit candidate recommendations and verify strict portfolio capital invariants."""
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        available_capital = 800000.0

        portfolio_request = {
            "available_capital": available_capital,
            "risk_profile": "MODERATE",
            "recommendations": [
                {
                    "ipo_id": "IPO-FIN-01",
                    "company_name": "Apex Microfinance Ltd",
                    "recommendation": "STRONG_SUBSCRIBE",
                    "composite_score": 86.0,
                    "confidence_score": 0.90,
                    "risk_level": "LOW",
                    "sector": "Financial Services",
                },
                {
                    "ipo_id": "IPO-HLT-01",
                    "company_name": "BioHealth Diagnostics Ltd",
                    "recommendation": "SUBSCRIBE",
                    "composite_score": 74.0,
                    "confidence_score": 0.85,
                    "risk_level": "MEDIUM",
                    "sector": "Healthcare",
                },
                {
                    "ipo_id": "IPO-MFG-01",
                    "company_name": "Steel Forging Works Ltd",
                    "recommendation": "NEUTRAL",
                    "composite_score": 52.0,
                    "confidence_score": 0.70,
                    "risk_level": "HIGH",
                    "sector": "Manufacturing",
                },
                {
                    "ipo_id": "IPO-AVD-01",
                    "company_name": "Distressed Power Ltd",
                    "recommendation": "AVOID",
                    "composite_score": 24.0,
                    "confidence_score": 0.80,
                    "risk_level": "VERY_HIGH",
                    "sector": "Power",
                },
            ],
        }

        alloc_resp = self.client.post("/portfolio/allocate", json=portfolio_request, headers=headers)
        self.assertEqual(alloc_resp.status_code, 200)
        data = alloc_resp.json()

        # Invariant 1: Total capital equals input capital
        self.assertEqual(data["total_capital"], available_capital)

        # Invariant 2: Total allocated capital never exceeds available capital
        self.assertLessEqual(data["total_allocated_capital"], available_capital)

        # Invariant 3: Cash remainder is non-negative
        self.assertGreaterEqual(data["unallocated_cash"], 0.0)

        # Invariant 4: Capital conservation (Allocated + Cash == Total Capital within 1 paisa)
        self.assertAlmostEqual(
            data["total_allocated_capital"] + data["unallocated_cash"],
            available_capital,
            places=2,
        )

        # Invariant 5: Single IPO exposure cap <= 35%
        for alloc in data["allocations"]:
            self.assertLessEqual(alloc["allocation_percentage"], 35.0)
            self.assertLessEqual(alloc["allocated_amount"], available_capital * 0.35 + 1e-4)

        # Invariant 6: Sector exposure cap <= 40%
        for sector, pct in data["sector_allocations"].items():
            self.assertLessEqual(pct, 40.0)

        # Invariant 7: AVOID recommendation gets zero capital
        avoid_alloc = next(a for a in data["allocations"] if a["ipo_id"] == "IPO-AVD-01")
        self.assertEqual(avoid_alloc["allocated_amount"], 0.0)
        self.assertEqual(avoid_alloc["allocation_percentage"], 0.0)

    # =========================================================================
    # Scenario D: Unauthenticated Request -> Correct 401 Rejection
    # =========================================================================
    def test_scenario_d_unauthenticated_requests_rejected(self):
        """Unauthenticated requests without headers must return HTTP 401 across all protected routes."""
        endpoints = [
            ("GET", "/ipos", None),
            ("GET", f"/ipos/{self.seed_ipo_id}", None),
            ("POST", "/recommendation/evaluate", {"ipo_id": self.seed_ipo_id}),
            ("POST", "/recommendation/validate", {"records": []}),
            ("POST", "/portfolio/allocate", {"available_capital": 100000, "recommendations": []}),
            ("GET", "/metrics", None),
        ]

        for method, path, body in endpoints:
            if method == "GET":
                resp = self.client.get(path)
            else:
                resp = self.client.post(path, json=body)

            self.assertEqual(resp.status_code, 401, f"Expected 401 for unauthenticated {method} {path}")
            data = resp.json()
            self.assertEqual(data["error"], "HTTP_EXCEPTION")
            self.assertIn("missing bearer token or x-api-key", data.get("detail", "").lower())

    # =========================================================================
    # Scenario E: READ_ONLY User -> Permitted Read & Denied Privileged Ops
    # =========================================================================
    def test_scenario_e_read_only_permitted_and_denied_boundaries(self):
        """READ_ONLY principal can read IPO catalog but cannot execute mutations or privileged operations."""
        headers = {"Authorization": f"Bearer {self.reader_token}"}

        # Permitted reads
        resp = self.client.get("/ipos", headers=headers)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(f"/ipos/{self.seed_ipo_id}", headers=headers)
        self.assertEqual(resp.status_code, 200)

        # Denied operations (Requires OPERATOR)
        resp = self.client.post("/recommendation/evaluate", json={"ipo_id": self.seed_ipo_id}, headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"], "HTTP_EXCEPTION")

        resp = self.client.post("/recommendation/validate", json={"records": []}, headers=headers)
        self.assertEqual(resp.status_code, 403)

        resp = self.client.post("/portfolio/allocate", json={"available_capital": 100000, "recommendations": []}, headers=headers)
        self.assertEqual(resp.status_code, 403)

        # Denied metrics (Requires ADMIN)
        resp = self.client.get("/metrics", headers=headers)
        self.assertEqual(resp.status_code, 403)

        # Verify OPERATOR also denied on ADMIN-only metrics
        op_headers = {"Authorization": f"Bearer {self.operator_token}"}
        resp = self.client.get("/metrics", headers=op_headers)
        self.assertEqual(resp.status_code, 403)

        # Verify ADMIN permitted on metrics
        adm_headers = {"Authorization": f"Bearer {self.admin_token}"}
        resp = self.client.get("/metrics", headers=adm_headers)
        self.assertEqual(resp.status_code, 200)

    # =========================================================================
    # Scenario F: Invalid, Missing, Malformed Inputs -> Controlled Errors (422)
    # =========================================================================
    def test_scenario_f_invalid_inputs_controlled_errors(self):
        """Malformed or invalid requests return controlled 422 errors without revealing internal tracebacks."""
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        # Malformed capital (negative value)
        resp = self.client.post(
            "/portfolio/allocate",
            json={"available_capital": -50000.0, "risk_profile": "MODERATE", "recommendations": []},
            headers=headers,
        )
        self.assertIn(resp.status_code, [400, 422])
        err = resp.json()
        self.assertIn("error", err)
        # Ensure no python traceback is leaked
        self.assertNotIn("Traceback (most recent call last)", json.dumps(err))

        # Invalid risk profile
        resp = self.client.post(
            "/portfolio/allocate",
            json={"available_capital": 100000.0, "risk_profile": "INVALID_RISK", "recommendations": []},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 422)

        # Empty body on evaluate
        resp = self.client.post("/recommendation/evaluate", json={}, headers=headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Either 'record' (JSON dict) or 'ipo_id' must be specified", resp.json()["detail"])

    # =========================================================================
    # Scenario G: Empty IPO Dataset & No Data Fabrication
    # =========================================================================
    def test_scenario_g_empty_dataset_and_no_fabrication(self):
        """When an unknown IPO is requested, system returns 404 without fabricating synthetic scores."""
        headers = {"Authorization": f"Bearer {self.reader_token}"}

        resp = self.client.get("/ipos/NON-EXISTENT-XYZ-999", headers=headers)
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertIn("not found", data["detail"].lower())

        # Recommendation evaluate with non-existent ID fails cleanly
        op_headers = {"Authorization": f"Bearer {self.operator_token}"}
        resp = self.client.post("/recommendation/evaluate", json={"ipo_id": "NON-EXISTENT-XYZ-999"}, headers=op_headers)
        self.assertEqual(resp.status_code, 404)

    # =========================================================================
    # Scenario H: Redis Outage -> Fail-Open (Standard) vs Fail-Closed (Expensive)
    # =========================================================================
    def test_scenario_h_redis_outage_fail_open_and_fail_closed(self):
        """Under Redis outage, standard reads fail-open while expensive calculations fail-closed (503)."""
        outage_cfg = SecurityConfig(
            environment="test",
            jwt_secret=self.jwt_secret,
            jwt_issuer=self.config.jwt_issuer,
            jwt_audience=self.config.jwt_audience,
            redis_url="redis://dead-redis:6379/0",
            rate_limit_fail_closed_expensive=True,
            trusted_hosts=["testserver"],
        )
        set_security_config(outage_cfg)
        redis_limiter = RedisRateLimiter("redis://dead-redis:6379/0", fallback=InMemoryRateLimiter())
        redis_limiter._init_failed = True
        set_rate_limiter(redis_limiter)

        try:
            outage_app = create_app(config=outage_cfg)
            outage_client = TestClient(outage_app)
            outage_token = create_access_token("outage-op", Role.OPERATOR, config=outage_cfg)
            headers = {"Authorization": f"Bearer {outage_token}"}

            # 1. Standard endpoint GET /ipos must fail-open to in-memory limiter (Status 200)
            resp = outage_client.get("/ipos", headers=headers)
            self.assertEqual(resp.status_code, 200)

            # 2. Expensive endpoint POST /recommendation/validate must fail-closed (Status 503)
            val_body = {"records": []}
            resp = outage_client.post("/recommendation/validate", json=val_body, headers=headers)
            self.assertEqual(resp.status_code, 503)
            self.assertEqual(resp.headers.get("Retry-After"), "30")
            self.assertIn("Service temporarily unavailable", resp.json()["detail"])
        finally:
            set_rate_limiter(InMemoryRateLimiter())
            set_security_config(self.config)

    # =========================================================================
    # Scenario I: Token Integrity (Expired, Tampered, Revoked)
    # =========================================================================
    def test_scenario_i_token_integrity_and_revocation(self):
        """Token validation strictly verifies expiration, cryptographic signature, and revocation state."""
        headers_func = lambda t: {"Authorization": f"Bearer {t}"}

        # 1. Expired token
        expired_token = create_access_token(
            "expired-user",
            Role.OPERATOR,
            expires_delta=timedelta(seconds=-60),
            config=self.config,
        )
        resp = self.client.get("/ipos", headers=headers_func(expired_token))
        self.assertEqual(resp.status_code, 401)
        self.assertIn("expired", resp.json().get("detail", "").lower())

        # 2. Tampered signature token
        tampered_token = self.operator_token[:-5] + "XXXXX"
        resp = self.client.get("/ipos", headers=headers_func(tampered_token))
        self.assertEqual(resp.status_code, 401)
        self.assertIn("invalid", resp.json().get("detail", "").lower())

        # 3. Revoked token (individual JTI)
        revocable_token = create_access_token("revocable-user", Role.OPERATOR, config=self.config)
        # Verify valid initially
        resp = self.client.get("/ipos", headers=headers_func(revocable_token))
        self.assertEqual(resp.status_code, 200)

        # Revoke the token JTI
        rev_store = get_revocation_store(self.config)
        decoded = jwt.decode(revocable_token, self.jwt_secret, algorithms=["HS256"], audience="ipo-api-test")
        jti = decoded["jti"]
        exp_ts = int(decoded["exp"])
        rev_store.revoke_token(jti, exp_ts)

        # Now must be rejected with 401
        resp = self.client.get("/ipos", headers=headers_func(revocable_token))
        self.assertEqual(resp.status_code, 401)
        self.assertIn("revoked", resp.json().get("detail", "").lower())

    # =========================================================================
    # Scenario J: Portfolio Allocation Regressions
    # =========================================================================
    def test_scenario_j_portfolio_allocation_regressions(self):
        """Validate critical portfolio regressions: duplicate IPO handling, fractional rounding, all-AVOID."""
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        # 1. Duplicate IPO identifier cannot bypass single-position cap (<= 35%)
        dup_request = {
            "available_capital": 1000000.0,
            "risk_profile": "AGGRESSIVE",
            "recommendations": [
                {
                    "ipo_id": "IPO-DUP-01",
                    "company_name": "Duplicated Corp Ltd",
                    "recommendation": "STRONG_SUBSCRIBE",
                    "composite_score": 92.0,
                    "confidence_score": 0.95,
                    "risk_level": "LOW",
                    "sector": "Technology",
                },
                {
                    "ipo_id": "IPO-DUP-01",
                    "company_name": "Duplicated Corp Ltd",
                    "recommendation": "STRONG_SUBSCRIBE",
                    "composite_score": 90.0,
                    "confidence_score": 0.90,
                    "risk_level": "LOW",
                    "sector": "Technology",
                },
            ],
        }
        resp = self.client.post("/portfolio/allocate", json=dup_request, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        dup_allocs = [a for a in data["allocations"] if a["ipo_id"] == "IPO-DUP-01"]
        self.assertEqual(len(dup_allocs), 1)
        self.assertLessEqual(dup_allocs[0]["allocation_percentage"], 35.0)
        self.assertLessEqual(dup_allocs[0]["allocated_amount"], 350000.0)

        # 2. Fractional capital with multiple positions: rounding invariant
        fractional_capital = 333333.33
        multi_request = {
            "available_capital": fractional_capital,
            "risk_profile": "MODERATE",
            "recommendations": [
                {
                    "ipo_id": f"IPO-FRAC-{i}",
                    "company_name": f"Frac Co {i}",
                    "recommendation": "STRONG_SUBSCRIBE" if i % 2 == 0 else "SUBSCRIBE",
                    "composite_score": 75.0 + i,
                    "confidence_score": 0.85,
                    "risk_level": "MEDIUM",
                    "sector": f"Sector-{i}",
                }
                for i in range(5)
            ],
        }
        resp = self.client.post("/portfolio/allocate", json=multi_request, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertLessEqual(data["total_allocated_capital"], fractional_capital)
        self.assertGreaterEqual(data["unallocated_cash"], 0.0)
        self.assertAlmostEqual(data["total_allocated_capital"] + data["unallocated_cash"], fractional_capital, places=2)

        # 3. All-AVOID cohort yields zero allocation and preserves 100% cash
        avoid_request = {
            "available_capital": 500000.0,
            "risk_profile": "CONSERVATIVE",
            "recommendations": [
                {
                    "ipo_id": "AVD-1",
                    "company_name": "Avoid One",
                    "recommendation": "AVOID",
                    "composite_score": 20.0,
                    "confidence_score": 0.8,
                    "risk_level": "HIGH",
                    "sector": "Real Estate",
                },
                {
                    "ipo_id": "AVD-2",
                    "company_name": "Avoid Two",
                    "recommendation": "AVOID",
                    "composite_score": 18.0,
                    "confidence_score": 0.8,
                    "risk_level": "VERY_HIGH",
                    "sector": "Retail",
                },
            ],
        }
        resp = self.client.post("/portfolio/allocate", json=avoid_request, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_allocated_capital"], 0.0)
        self.assertEqual(data["unallocated_cash"], 500000.0)

    # =========================================================================
    # Scenario K: Health Endpoint Information Leakage Check
    # =========================================================================
    def test_scenario_k_health_probe_sanitization(self):
        """GET /health probe provides system health status without exposing sensitive infrastructure info."""
        resp = self.client.get("/health")
        self.assertIn(resp.status_code, [200, 503])
        data = resp.json()

        self.assertIn("status", data)
        self.assertIn("checks", data)
        self.assertIn("database", data["checks"])

        # Check raw payload strings for forbidden substrings
        serialized = json.dumps(data)
        self.assertNotIn("secret_pass123", serialized)
        self.assertNotIn("password=", serialized.lower())
        self.assertNotIn("postgresql://", serialized)
        self.assertNotIn("sqlite:///", serialized)

    # =========================================================================
    # Scenario L: Observability Metrics & Credential Safety
    # =========================================================================
    def test_scenario_l_metrics_and_log_credential_safety(self):
        """GET /metrics delivers monitoring counters without leaking authorization tokens or API keys."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        resp = self.client.get("/metrics", headers=headers)
        self.assertEqual(resp.status_code, 200)
        metrics = resp.json()

        self.assertIn("counters", metrics)
        self.assertIn("timestamp", metrics)

        # Ensure no credential leakage in serialized metrics
        raw_metrics = json.dumps(metrics)
        self.assertNotIn(self.jwt_secret, raw_metrics)
        self.assertNotIn("key-reader-e2e", raw_metrics)
        self.assertNotIn("key-operator-e2e", raw_metrics)
        self.assertNotIn("key-admin-e2e", raw_metrics)

    # =========================================================================
    # Scenario M: Web Dashboard Delivery and Security Headers
    # =========================================================================
    def test_scenario_m_web_dashboard_delivery_and_csp(self):
        """Verifies native dashboard UI is delivered at GET / and GET /dashboard with compliant CSP."""
        for path in ["/", "/dashboard"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.headers["content-type"])
            content = resp.text

            # Check key interface sections
            self.assertIn("Indian IPO Intelligence", content)
            self.assertIn("IPO Offerings", content)
            self.assertIn("Recommendation Engine", content)
            self.assertIn("Portfolio Allocator", content)
            self.assertIn("System Health & Telemetry", content)

            # Check CSP header allows self and fonts while protecting frame-ancestors
            csp = resp.headers.get("Content-Security-Policy", "")
            self.assertIn("default-src 'self'", csp)
            self.assertIn("frame-ancestors 'none'", csp)
            self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
            self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")


if __name__ == "__main__":
    unittest.main()
