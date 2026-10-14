"""
Comprehensive Security & Production Hardening Test Suite (Phase 10 - Stage 5).
Validates:
1. Authentication (JWT, API Keys, token tampering, expiration, signature verification)
2. RBAC Authorization (READ_ONLY, OPERATOR, ADMIN privilege boundaries)
3. Rate Limiting & Abuse Prevention (sliding window, 429 Retry-After, fail-safe degradation)
4. CORS & Host Header Security (origin checks, credential safety, host spoofing)
5. HTTP Security Headers (X-Content-Type-Options, X-Frame-Options, CSP, Cache-Control)
6. Payload & Request Hardening (max body size 413, regex ID checks, numeric bounds)
7. Information Leakage & Error Sanitization (no credentials/SQL in responses)
8. Production Config Validation (fail-fast on insecure defaults)
"""

from datetime import datetime, timedelta, timezone
import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient
import jwt
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ipo_platform.api.app import create_app
from ipo_platform.api.dependencies import set_db_engine
from ipo_platform.db.base import Base
from ipo_platform.db.exceptions import PlatformDatabaseError
from ipo_platform.db.session import get_engine
from ipo_platform.security.auth import (
    AuthenticatedPrincipal,
    create_access_token,
    decode_access_token,
    validate_api_key,
)
from ipo_platform.security.config import SecurityConfig, set_security_config
from ipo_platform.security.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    get_rate_limiter,
    set_rate_limiter,
)
from ipo_platform.security.rbac import Role, has_sufficient_role


class TestSecuritySuite(unittest.TestCase):
    """Zero-trust security and RBAC validation test cases."""

    @classmethod
    def setUpClass(cls):
        cls.test_engine = get_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.test_engine)
        set_db_engine(cls.test_engine)

        cls.jwt_secret = "test-secret-key-32-characters-minimum-for-testing-12345!"
        cls.api_keys = {
            "key-readonly-123": "READ_ONLY",
            "key-operator-456": "OPERATOR",
            "key-admin-789": "ADMIN",
        }

        cls.config = SecurityConfig(
            environment="test",
            auth_enabled=True,
            jwt_secret=cls.jwt_secret,
            jwt_algorithm="HS256",
            jwt_issuer="ipo-platform-test",
            jwt_audience="ipo-api-test",
            api_keys=cls.api_keys,
            cors_allowed_origins=["https://dashboard.ipo-platform.com"],
            cors_allow_credentials=True,
            trusted_hosts=["testserver", "localhost", "127.0.0.1"],
            rate_limit_enabled=True,
            rate_limit_unauthenticated_rpm=5,
            rate_limit_authenticated_rpm=10,
            rate_limit_expensive_rpm=2,
            max_request_body_bytes=1024 * 1024,  # 1 MB
            docs_enabled=True,
        )
        set_security_config(cls.config)
        cls.app = create_app(config=cls.config)
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.test_engine)
        set_db_engine(None)
        set_security_config(None)

    def setUp(self):
        # Reset security config, rate limiter, and revocation store before each test
        set_security_config(self.config)
        set_rate_limiter(None)
        limiter = get_rate_limiter(self.config)
        limiter.reset()
        from ipo_platform.security.auth import get_revocation_store
        get_revocation_store(self.config).reset()

    def tearDown(self):
        set_security_config(self.config)
        set_rate_limiter(None)
        from ipo_platform.security.auth import get_revocation_store
        get_revocation_store(self.config).reset()

    # =========================================================================
    # 1. AUTHENTICATION TESTS
    # =========================================================================

    def test_missing_credentials_returns_401(self):
        """Endpoints requiring authentication return 401 when no credentials are provided."""
        response = self.client.get("/ipos")
        self.assertEqual(response.status_code, 401)
        self.assertIn("WWW-Authenticate", response.headers)
        self.assertIn("Authentication required", response.json().get("detail", ""))

    def test_malformed_authorization_header_returns_401(self):
        """Malformed Authorization headers (e.g. not Bearer) are rejected with 401."""
        response = self.client.get("/ipos", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Expected 'Bearer <token>'", response.json().get("detail", ""))

    def test_invalid_signature_token_returns_401(self):
        """Tokens signed with a different key are rejected with 401."""
        forged_token = jwt.encode(
            {"sub": "attacker", "role": "ADMIN", "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
             "iat": int(datetime.now(timezone.utc).timestamp()), "iss": "ipo-platform-test", "aud": "ipo-api-test"},
            "wrong-untrusted-secret-key-attacker-signature!",
            algorithm="HS256",
        )
        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid authentication token", response.json().get("detail", ""))

    def test_expired_token_returns_401(self):
        """Expired JWT tokens are rejected with 401 and standard error description."""
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        expired_token = jwt.encode(
            {"sub": "expired-user", "role": "OPERATOR", "iat": int(past.timestamp()),
             "nbf": int(past.timestamp()), "exp": int(past.timestamp()) + 60,
             "iss": "ipo-platform-test", "aud": "ipo-api-test"},
            self.jwt_secret,
            algorithm="HS256",
        )
        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json().get("detail", "").lower())

    def test_wrong_issuer_returns_401(self):
        """Tokens with mismatched issuer claim are rejected."""
        token = jwt.encode(
            {"sub": "user1", "role": "READ_ONLY", "iat": int(datetime.now(timezone.utc).timestamp()),
             "nbf": int(datetime.now(timezone.utc).timestamp()),
             "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
             "iss": "untrusted-issuer", "aud": "ipo-api-test"},
            self.jwt_secret,
            algorithm="HS256",
        )
        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)

    def test_wrong_audience_returns_401(self):
        """Tokens with mismatched audience claim are rejected."""
        token = jwt.encode(
            {"sub": "user1", "role": "READ_ONLY", "iat": int(datetime.now(timezone.utc).timestamp()),
             "nbf": int(datetime.now(timezone.utc).timestamp()),
             "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
             "iss": "ipo-platform-test", "aud": "different-target-api"},
            self.jwt_secret,
            algorithm="HS256",
        )
        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)

    def test_valid_api_key_authenticates_successfully(self):
        """Valid X-API-Key header authenticates and assigns configured role."""
        response = self.client.get("/ipos", headers={"X-API-Key": "key-readonly-123"})
        self.assertEqual(response.status_code, 200)

    def test_invalid_api_key_returns_401(self):
        """Invalid X-API-Key header returns 401."""
        response = self.client.get("/ipos", headers={"X-API-Key": "unrecognized-bogus-key"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid API key")

    # =========================================================================
    # 2. RBAC AUTHORIZATION TESTS
    # =========================================================================

    def test_read_only_can_access_read_endpoints(self):
        """READ_ONLY principal can access GET /ipos."""
        token = create_access_token("reader-1", Role.READ_ONLY, config=self.config)
        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)

    def test_read_only_forbidden_from_operator_evaluate_endpoint(self):
        """READ_ONLY principal receives 403 when attempting POST /recommendation/evaluate."""
        token = create_access_token("reader-1", Role.READ_ONLY, config=self.config)
        response = self.client.post(
            "/recommendation/evaluate",
            headers={"Authorization": f"Bearer {token}"},
            json={"ipo_id": "TEST-IPO"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("insufficient permissions", response.json()["detail"].lower())

    def test_read_only_forbidden_from_operator_allocate_endpoint(self):
        """READ_ONLY principal receives 403 when attempting POST /portfolio/allocate."""
        token = create_access_token("reader-1", Role.READ_ONLY, config=self.config)
        response = self.client.post(
            "/portfolio/allocate",
            headers={"Authorization": f"Bearer {token}"},
            json={"available_capital": 100000.0, "risk_profile": "MODERATE"},
        )
        self.assertEqual(response.status_code, 403)

    def test_read_only_forbidden_from_admin_metrics_endpoint(self):
        """READ_ONLY principal receives 403 when attempting GET /metrics."""
        token = create_access_token("reader-1", Role.READ_ONLY, config=self.config)
        response = self.client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)

    def test_operator_can_access_recommendation_and_portfolio_endpoints(self):
        """OPERATOR principal can access evaluate and allocate."""
        token = create_access_token("operator-1", Role.OPERATOR, config=self.config)
        # Evaluate with 404 (valid auth and authorization, but missing ID in DB)
        response = self.client.post(
            "/recommendation/evaluate",
            headers={"Authorization": f"Bearer {token}"},
            json={"ipo_id": "NON-EXISTENT"},
        )
        self.assertEqual(response.status_code, 404)

        # Allocate with empty input succeeds (returns 0 allocations)
        response_alloc = self.client.post(
            "/portfolio/allocate",
            headers={"Authorization": f"Bearer {token}"},
            json={"available_capital": 50000.0, "risk_profile": "CONSERVATIVE", "recommendations": []},
        )
        self.assertEqual(response_alloc.status_code, 200)

    def test_operator_forbidden_from_admin_metrics_endpoint(self):
        """OPERATOR principal receives 403 when attempting GET /metrics."""
        token = create_access_token("operator-1", Role.OPERATOR, config=self.config)
        response = self.client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_all_endpoints(self):
        """ADMIN principal can access GET /metrics as well as all other endpoints."""
        token = create_access_token("admin-1", Role.ADMIN, config=self.config)
        response = self.client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)

        response_ipos = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response_ipos.status_code, 200)

    # =========================================================================
    # 3. RATE LIMITING & ABUSE PROTECTION TESTS
    # =========================================================================

    def test_rate_limiting_blocks_when_threshold_exceeded(self):
        """Reaching rate limit triggers HTTP 429 with standard Retry-After header."""
        token = create_access_token("rate-user", Role.READ_ONLY, config=self.config)
        # rate_limit_authenticated_rpm is 10
        for _ in range(10):
            res = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(res.status_code, 200)

        # 11th request must fail with 429
        rejected = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(rejected.status_code, 429)
        self.assertIn("Retry-After", rejected.headers)
        self.assertIn("X-RateLimit-Limit", rejected.headers)
        self.assertEqual(rejected.headers["X-RateLimit-Remaining"], "0")

    def test_rate_limiter_fail_safe_redis_fallback(self):
        """Redis failure does not crash the API; gracefully falls back to in-memory tracking."""
        in_memory = InMemoryRateLimiter()
        # Create Redis limiter pointing to dead connection
        redis_limiter = RedisRateLimiter("redis://invalid-host-definitely-dead:6379/0", fallback=in_memory)
        res = redis_limiter.check("test-key", limit=5, window_seconds=60)
        self.assertTrue(res.allowed)
        self.assertEqual(res.remaining, 4)

    def test_rate_limiter_reconnect_cooldown(self):
        """Redis limiter retries initialization after cooldown interval when initial connection failed."""
        in_memory = InMemoryRateLimiter()
        redis_limiter = RedisRateLimiter("redis://invalid-host-definitely-dead:6379/0", fallback=in_memory)
        self.assertTrue(redis_limiter._init_failed)

        # Advance time past retry cooldown
        redis_limiter._last_retry_time = time.time() - 35.0
        with patch.object(redis_limiter, "_init_client") as mock_init:
            redis_limiter.check("test-retry", limit=5, window_seconds=60)
            mock_init.assert_called_once()

    # =========================================================================
    # 4. CORS & HOST HEADER SECURITY TESTS
    # =========================================================================

    def test_cors_headers_for_allowed_origin(self):
        """Preflight OPTIONS request from configured origin succeeds with CORS headers."""
        response = self.client.options(
            "/ipos",
            headers={
                "Origin": "https://dashboard.ipo-platform.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "https://dashboard.ipo-platform.com")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_rejects_wildcard_with_credentials_in_prod(self):
        """SecurityConfig raises ValueError if wildcard '*' is combined with credentials in production."""
        with self.assertRaises(ValueError) as ctx:
            SecurityConfig(
                environment="production",
                auth_enabled=True,
                jwt_secret="strong-prod-secret-minimum-32-chars-long-strictly!",
                cors_allowed_origins=["*"],
                cors_allow_credentials=True,
            )
        self.assertIn("cannot contain wildcard '*'", str(ctx.exception))

    def test_production_fails_fast_on_insecure_default_secret(self):
        """Production startup fails if dev default JWT secret is used."""
        with self.assertRaises(ValueError) as ctx:
            SecurityConfig(
                environment="production",
                auth_enabled=True,
                jwt_secret="dev-insecure-secret-change-in-production-only-32bytes!",
            )
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", str(ctx.exception))

    # =========================================================================
    # 5. SECURITY HEADERS TESTS
    # =========================================================================

    def test_http_security_headers_present(self):
        """Ensures modern defense-in-depth security headers are present on responses."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("default-src 'self'", response.headers.get("Content-Security-Policy", ""))

    def test_cache_control_no_store_on_sensitive_routes(self):
        """Sensitive endpoints output Cache-Control: no-store."""
        token = create_access_token("admin", Role.ADMIN, config=self.config)
        response = self.client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    # =========================================================================
    # 6. PAYLOAD SIZE & INPUT HARDENING TESTS
    # =========================================================================

    def test_payload_too_large_rejected_with_413(self):
        """Requests with Content-Length exceeding max_request_body_bytes return 413."""
        token = create_access_token("admin", Role.ADMIN, config=self.config)
        oversized_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Length": str(self.config.max_request_body_bytes + 1000),
            "Content-Type": "application/json",
        }
        response = self.client.post("/portfolio/allocate", headers=oversized_headers, content=b"{}")
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"], "PAYLOAD_TOO_LARGE")

    def test_invalid_ipo_id_pattern_rejected(self):
        """Path traversal or dangerous characters in IPO ID are rejected."""
        token = create_access_token("reader", Role.READ_ONLY, config=self.config)
        # Attempting path traversal in ipo_id
        response = self.client.get("/ipos/../../etc/passwd", headers={"Authorization": f"Bearer {token}"})
        # FastAPI routing or regex rejects traversal before querying DB
        self.assertIn(response.status_code, (404, 422))

    def test_negative_or_zero_available_capital_rejected(self):
        """Non-positive capital in allocation request is rejected with 422."""
        token = create_access_token("operator", Role.OPERATOR, config=self.config)
        response = self.client.post(
            "/portfolio/allocate",
            headers={"Authorization": f"Bearer {token}"},
            json={"available_capital": -500.0, "risk_profile": "MODERATE"},
        )
        self.assertEqual(response.status_code, 422)

    def test_pathological_capital_exceeding_max_rejected(self):
        """Capital exceeding 1 trillion INR is rejected with 422."""
        token = create_access_token("operator", Role.OPERATOR, config=self.config)
        response = self.client.post(
            "/portfolio/allocate",
            headers={"Authorization": f"Bearer {token}"},
            json={"available_capital": 1e13, "risk_profile": "MODERATE"},
        )
        self.assertEqual(response.status_code, 422)

    # =========================================================================
    # 7. INFORMATION LEAKAGE & ERROR SANITIZATION
    # =========================================================================

    def test_database_error_does_not_leak_internals_or_credentials(self):
        """Database errors return generic sanitized message without SQL or connection strings."""
        token = create_access_token("reader", Role.READ_ONLY, config=self.config)

        from ipo_platform.api.dependencies import get_query_service
        mock_inst = MagicMock()
        mock_inst.list_active_ipos.side_effect = PlatformDatabaseError(
            "CRITICAL: Failed query SELECT * FROM users WHERE pass='secret_pass123' at 192.168.1.50"
        )
        self.app.dependency_overrides[get_query_service] = lambda: mock_inst
        try:
            response = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        finally:
            self.app.dependency_overrides.clear()

            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["error"], "DATABASE_ERROR")
            # Detail must be sanitized
            self.assertEqual(data["detail"], "A database error occurred while processing the request")
            self.assertNotIn("secret_pass123", json.dumps(data))
            self.assertNotIn("SELECT", json.dumps(data))

    # =========================================================================
    # 8. STAGE 3 PORTFOLIO REGRESSION VERIFICATION VIA API
    # =========================================================================

    def test_portfolio_duplicate_ipo_prevention_via_api(self):
        """Duplicate IPO IDs in allocation payload must not bypass single-IPO cap."""
        token = create_access_token("operator", Role.OPERATOR, config=self.config)
        recs = [
            {
                "ipo_id": "DUP-IPO-01",
                "company_name": "Duplicate Inc",
                "recommendation": "STRONG_SUBSCRIBE",
                "composite_score": 90.0,
                "confidence_score": 0.9,
                "risk_level": "LOW",
                "sector": "Technology",
            },
            {
                "ipo_id": "DUP-IPO-01",
                "company_name": "Duplicate Inc",
                "recommendation": "STRONG_SUBSCRIBE",
                "composite_score": 85.0,
                "confidence_score": 0.8,
                "risk_level": "LOW",
                "sector": "Technology",
            },
        ]
        response = self.client.post(
            "/portfolio/allocate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "available_capital": 100000.0,
                "risk_profile": "AGGRESSIVE",
                "recommendations": recs,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # There should only be 1 consolidated allocation for DUP-IPO-01
        self.assertEqual(len(data["allocations"]), 1)
        self.assertEqual(data["allocations"][0]["ipo_id"], "DUP-IPO-01")
        # Allocation percentage must not exceed 35%
        self.assertLessEqual(data["allocations"][0]["allocation_percentage"], 35.0)

    def test_portfolio_rounding_does_not_exceed_100_percent_via_api(self):
        """Sum of percentages must never exceed 100.0% and sum of allocated capital <= available."""
        token = create_access_token("operator", Role.OPERATOR, config=self.config)
        recs = [
            {
                "ipo_id": f"ROUND-IPO-{i}",
                "company_name": f"Round Inc {i}",
                "recommendation": "STRONG_SUBSCRIBE",
                "composite_score": 90.0,
                "confidence_score": 0.9,
                "risk_level": "LOW",
                "sector": f"Sector-{i}",
            }
            for i in range(5)
        ]
        response = self.client.post(
            "/portfolio/allocate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "available_capital": 100000.0,
                "risk_profile": "AGGRESSIVE",
                "recommendations": recs,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(data["total_allocation_percentage"], 100.0)
        self.assertLessEqual(data["total_allocated_capital"], 100000.0)
        self.assertAlmostEqual(
            data["total_allocated_capital"] + data["unallocated_cash"],
            100000.0,
            places=2,
        )

    # =========================================================================
    # 9. JWT REVOCATION REGRESSION TESTS
    # =========================================================================

    def test_revoked_token_by_jti_is_rejected(self):
        """Tokens revoked by unique JTI return 401."""
        from ipo_platform.security.auth import get_revocation_store
        token = create_access_token("revoked_user", Role.READ_ONLY, config=self.config)
        # Decode once to get claims/JTI
        payload = jwt.decode(token, self.config.jwt_secret, algorithms=["HS256"], audience=self.config.jwt_audience)
        jti = payload["jti"]

        # Revoke this JTI
        store = get_revocation_store(self.config)
        store.revoke_token(jti, expires_at=time.time() + 3600)

        # Attempting to call API with this revoked token must fail with 401
        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("revoked", response.json().get("detail", "").lower())

    def test_revoked_user_tokens_are_rejected(self):
        """Revoking all tokens for a user invalidates previously issued tokens."""
        from ipo_platform.security.auth import get_revocation_store
        token = create_access_token("user_to_revoke", Role.READ_ONLY, config=self.config)
        time.sleep(1)  # Ensure timestamp advances
        store = get_revocation_store(self.config)
        store.revoke_user_tokens("user_to_revoke")

        response = self.client.get("/ipos", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("revoked", response.json().get("detail", "").lower())

    def test_revocation_redis_failure_fail_closed_behavior(self):
        """When jwt_revocation_fail_closed is True and Redis fails, token decode raises PyJWTError."""
        from ipo_platform.security.auth import TokenRevocationStore
        fail_closed_cfg = SecurityConfig(
            environment="test",
            jwt_secret=self.jwt_secret,
            redis_url="redis://unreachable-redis-host:6379/0",
            jwt_revocation_enabled=True,
            jwt_revocation_fail_closed=True,
        )
        store = TokenRevocationStore(fail_closed_cfg)
        store._redis_client = MagicMock()
        store._redis_failed = False
        store._redis_client.get.side_effect = Exception("Redis connection timed out")

        with self.assertRaises(jwt.PyJWTError):
            store.is_revoked("any-jti", "any-user", int(time.time()))

    # =========================================================================
    # 10. X-FORWARDED-FOR & PROXY TRUST REGRESSION TESTS
    # =========================================================================

    def test_client_ip_ignores_untrusted_forwarded_for(self):
        """Arbitrary X-Forwarded-For headers from untrusted clients are ignored to prevent spoofing."""
        from ipo_platform.security.rate_limiter import get_client_identifier
        req = MagicMock()
        req.client.host = "192.168.1.100"
        req.headers = {"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}

        cfg_untrusted = SecurityConfig(trust_proxy_headers=False, trusted_proxies=[])
        client_id = get_client_identifier(req, principal=None, config=cfg_untrusted)
        # Must resolve to peer IP (192.168.1.100), NOT spoofed 203.0.113.195
        self.assertEqual(client_id, "ip:192.168.1.100")

    def test_client_ip_trusts_forwarded_for_when_configured(self):
        """X-Forwarded-For is trusted when proxy trust is enabled or peer is in trusted_proxies."""
        from ipo_platform.security.rate_limiter import get_client_identifier
        req = MagicMock()
        req.client.host = "10.0.0.1"  # Reverse proxy peer IP
        req.headers = {"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}

        # Case A: trust_proxy_headers = True
        cfg_trusted_headers = SecurityConfig(trust_proxy_headers=True)
        client_id_a = get_client_identifier(req, principal=None, config=cfg_trusted_headers)
        self.assertEqual(client_id_a, "ip:203.0.113.195")

        # Case B: peer in trusted_proxies
        cfg_trusted_proxy_list = SecurityConfig(trust_proxy_headers=False, trusted_proxies=["10.0.0.1"])
        client_id_b = get_client_identifier(req, principal=None, config=cfg_trusted_proxy_list)
        self.assertEqual(client_id_b, "ip:203.0.113.195")

    # =========================================================================
    # 11. RATE LIMITING OUTAGE POLICY REGRESSION TESTS
    # =========================================================================

    def test_rate_limiter_outage_fail_closed_on_expensive_endpoint(self):
        """When rate_limit_fail_closed_expensive is True and Redis is down, expensive endpoint returns 503."""
        from ipo_platform.security.rate_limiter import set_rate_limiter, RedisRateLimiter, InMemoryRateLimiter
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
            app = create_app(config=outage_cfg)
            client = TestClient(app)

            token = create_access_token("operator", Role.OPERATOR, config=outage_cfg)

            # Calling expensive endpoint POST /recommendation/validate
            response = client.post(
                "/recommendation/validate",
                headers={"Authorization": f"Bearer {token}"},
                json={"records": []},
            )
            # Must return 503 Service Unavailable due to explicit fail-closed policy
            self.assertEqual(response.status_code, 503)
            self.assertIn("Retry-After", response.headers)
            self.assertIn("Service temporarily unavailable", response.json()["detail"])
        finally:
            set_rate_limiter(None)
            set_security_config(self.config)

    def test_user_revocation_allows_newly_issued_tokens(self):
        """Tokens issued AFTER a user revocation event are valid and accepted."""
        from ipo_platform.security.auth import get_revocation_store
        token_old = create_access_token("user_rotated", Role.READ_ONLY, config=self.config)
        time.sleep(0.01)
        store = get_revocation_store(self.config)
        store.revoke_user_tokens("user_rotated")
        time.sleep(0.01)
        token_new = create_access_token("user_rotated", Role.READ_ONLY, config=self.config)

        # Old token must be rejected with 401 revoked
        res_old = self.client.get("/ipos", headers={"Authorization": f"Bearer {token_old}"})
        self.assertEqual(res_old.status_code, 401)
        self.assertIn("revoked", res_old.json().get("detail", "").lower())

        # New token must succeed with 200
        res_new = self.client.get("/ipos", headers={"Authorization": f"Bearer {token_new}"})
        self.assertEqual(res_new.status_code, 200)

    def test_client_ip_trusts_cidr_proxies(self):
        """Peer IPs matching trusted CIDR blocks (e.g. 10.0.0.0/8) correctly trust X-Forwarded-For."""
        from ipo_platform.security.rate_limiter import get_client_identifier
        req_in_cidr = MagicMock()
        req_in_cidr.client.host = "10.244.15.30"
        req_in_cidr.headers = {"X-Forwarded-For": "198.51.100.77, 10.244.15.30"}

        cfg_cidr = SecurityConfig(trust_proxy_headers=False, trusted_proxies=["127.0.0.1", "10.0.0.0/8"])
        client_id_cidr = get_client_identifier(req_in_cidr, principal=None, config=cfg_cidr)
        self.assertEqual(client_id_cidr, "ip:198.51.100.77")

        # Peer outside CIDR is not trusted
        req_outside = MagicMock()
        req_outside.client.host = "192.168.1.50"
        req_outside.headers = {"X-Forwarded-For": "198.51.100.77, 192.168.1.50"}
        client_id_outside = get_client_identifier(req_outside, principal=None, config=cfg_cidr)
        self.assertEqual(client_id_outside, "ip:192.168.1.50")

    def test_rate_limiter_recovery_after_redis_reconnect(self):
        """RedisRateLimiter attempts reconnect and recovers when Redis comes back online."""
        from ipo_platform.security.rate_limiter import RedisRateLimiter, InMemoryRateLimiter
        limiter = RedisRateLimiter("redis://reconnecting-redis:6379/0", fallback=InMemoryRateLimiter())
        limiter._init_failed = True
        limiter._last_retry_time = time.time() - 35.0  # Elapse the 30s retry interval

        # Mock successful reconnect
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client
        with patch.dict("sys.modules", {"redis": mock_redis}):
            available = limiter.is_available()
            self.assertTrue(available)
            self.assertFalse(limiter._init_failed)

    def test_token_revocation_recovery_after_redis_reconnect(self):
        """TokenRevocationStore attempts reconnect and clears failure flag when Redis recovers."""
        from ipo_platform.security.auth import TokenRevocationStore
        cfg = SecurityConfig(environment="test", jwt_secret=self.jwt_secret, redis_url="redis://recovery-redis:6379/0")
        store = TokenRevocationStore(cfg)
        store._redis_failed = True
        store._last_retry_time = time.time() - 35.0  # Elapse retry interval

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client
        with patch.dict("sys.modules", {"redis": mock_redis}):
            is_rev = store.is_revoked("test-jti", "test-user", time.time())
            self.assertFalse(is_rev)
            self.assertFalse(store._redis_failed)

    def test_in_memory_rate_limiter_concurrency_atomicity(self):
        """Concurrent requests against InMemoryRateLimiter cannot exceed configured threshold."""
        import concurrent.futures
        limiter = InMemoryRateLimiter()
        limit = 15
        key = "concurrent-test-key"

        def attempt_check():
            res = limiter.check(key, limit=limit, window_seconds=60)
            return res.allowed

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(attempt_check) for _ in range(50)]
            results = [f.result() for f in futures]

        allowed_count = sum(1 for r in results if r is True)
        rejected_count = sum(1 for r in results if r is False)
        self.assertEqual(allowed_count, 15)
        self.assertEqual(rejected_count, 35)


if __name__ == "__main__":
    unittest.main()
