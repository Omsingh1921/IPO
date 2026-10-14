"""
Security & Authentication Configuration for Indian IPO Platform (Phase 10 - Stage 5).
Manages centralized security settings, JWT secrets, RBAC rules, CORS, rate limits, and headers.
All sensitive settings are loaded from environment variables with safe development defaults.
"""

from dataclasses import dataclass, field
import os
import secrets
from typing import Dict, List, Optional


@dataclass
class SecurityConfig:
    """Centralized security configuration container."""

    # Environment
    environment: str = field(
        default_factory=lambda: os.getenv("IPO_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")).lower()
    )

    # Master authentication switch
    auth_enabled: bool = field(
        default_factory=lambda: os.getenv("AUTH_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    # JWT Settings
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET", "dev-insecure-secret-change-in-production-only-32bytes!")
    )
    jwt_algorithm: str = field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )
    jwt_access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )
    jwt_issuer: str = field(
        default_factory=lambda: os.getenv("JWT_ISSUER", "ipo-platform")
    )
    jwt_audience: str = field(
        default_factory=lambda: os.getenv("JWT_AUDIENCE", "ipo-platform-api")
    )

    # API Keys Configuration: mapping of API Key to assigned Role name
    # Pre-configured keys from environment or generated for dev/test
    api_keys: Dict[str, str] = field(default_factory=dict)

    # CORS Settings
    cors_allowed_origins: List[str] = field(default_factory=list)
    cors_allow_credentials: bool = field(
        default_factory=lambda: os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() in ("true", "1", "yes")
    )
    cors_allowed_methods: List[str] = field(
        default_factory=lambda: ["GET", "POST", "OPTIONS"]
    )
    cors_allowed_headers: List[str] = field(
        default_factory=lambda: [
            "Authorization",
            "X-API-Key",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-Client-Version",
        ]
    )

    # Trusted Host Settings
    trusted_hosts: List[str] = field(default_factory=list)

    # Rate Limiting Settings
    rate_limit_enabled: bool = field(
        default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    rate_limit_unauthenticated_rpm: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_UNAUTHENTICATED_RPM", "60"))
    )
    rate_limit_authenticated_rpm: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_AUTHENTICATED_RPM", "180"))
    )
    rate_limit_expensive_rpm: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_EXPENSIVE_RPM", "20"))
    )
    redis_url: Optional[str] = field(
        default_factory=lambda: os.getenv("REDIS_URL", None)
    )

    # JWT Revocation Settings
    jwt_revocation_enabled: bool = field(
        default_factory=lambda: os.getenv("JWT_REVOCATION_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    # Fail-closed policy for JWT revocation during Redis outages.
    # When False (fail-open/default): falls back to local in-memory revocation store.
    # NOTE ON CROSS-POD LIMITATION: In fail-open mode, revocations performed on one pod
    # do NOT propagate across pods unless Redis is operational. In multi-pod production,
    # REDIS_URL is mandatory for synchronized revocation.
    jwt_revocation_fail_closed: bool = field(
        default_factory=lambda: os.getenv("JWT_REVOCATION_FAIL_CLOSED", "false").lower() in ("true", "1", "yes")
    )

    # Proxy and Forwarded Headers Trust
    # When trust_proxy_headers is True or peer IP matches trusted_proxies (IP or CIDR),
    # X-Forwarded-For headers are trusted for client IP extraction.
    trust_proxy_headers: bool = field(
        default_factory=lambda: os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("true", "1", "yes")
    )
    trusted_proxies: List[str] = field(default_factory=list)

    # Outage Policy for Rate Limiting
    # When True, high-cost endpoints (such as /recommendation/validate) return HTTP 503
    # during Redis outages instead of falling open, protecting worker CPU/memory.
    rate_limit_fail_closed_expensive: bool = field(
        default_factory=lambda: os.getenv("RATE_LIMIT_FAIL_CLOSED_EXPENSIVE", "false").lower() in ("true", "1", "yes")
    )

    # Request Hardening Settings
    max_request_body_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_REQUEST_BODY_BYTES", str(2 * 1024 * 1024)))  # 2 MB default
    )
    # HTTPS & HSTS Policy
    # NOTE: enforce_https injects Strict-Transport-Security (HSTS) headers into responses.
    # It does NOT perform server TLS termination; physical TLS termination and HTTP->HTTPS
    # redirection must be handled upstream by the reverse proxy (e.g. AWS ALB, NGINX, Cloudflare).
    enforce_https: bool = field(
        default_factory=lambda: os.getenv("ENFORCE_HTTPS", "false").lower() in ("true", "1", "yes")
    )

    # Documentation exposure
    docs_enabled: bool = field(
        default_factory=lambda: os.getenv("DOCS_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    def __post_init__(self) -> None:
        """Parses complex env vars and executes fail-fast security validation."""
        # 1. Parse CORS Allowed Origins
        if not self.cors_allowed_origins:
            raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
            if raw_origins.strip():
                self.cors_allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
            else:
                if self.is_production:
                    self.cors_allowed_origins = []  # In production, must be explicitly configured
                else:
                    self.cors_allowed_origins = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]

        # 2. Parse Trusted Hosts
        if not self.trusted_hosts:
            raw_hosts = os.getenv("TRUSTED_HOSTS", "")
            if raw_hosts.strip():
                self.trusted_hosts = [h.strip() for h in raw_hosts.split(",") if h.strip()]
            else:
                if self.is_production:
                    self.trusted_hosts = ["ipo-platform.internal", "api.ipo-platform.com"]
                else:
                    self.trusted_hosts = ["*"]  # Development / Test allows all hosts

        # 3. Parse API Keys from environment
        if not self.api_keys:
            # Format: API_KEYS="key1:READ_ONLY,key2:OPERATOR,key3:ADMIN"
            raw_keys = os.getenv("API_KEYS", "")
            if raw_keys.strip():
                for pair in raw_keys.split(","):
                    if ":" in pair:
                        k, r = pair.split(":", 1)
                        if k.strip() and r.strip():
                            self.api_keys[k.strip()] = r.strip().upper()

            # Dedicated per-role keys
            for role_name in ["READ_ONLY", "OPERATOR", "ADMIN"]:
                env_key = os.getenv(f"API_KEY_{role_name}", "")
                if env_key.strip():
                    self.api_keys[env_key.strip()] = role_name

        # 4. Parse Trusted Proxies from environment
        if not self.trusted_proxies:
            raw_proxies = os.getenv("TRUSTED_PROXIES", "")
            if raw_proxies.strip():
                self.trusted_proxies = [p.strip() for p in raw_proxies.split(",") if p.strip()]

        # 5. In production, docs should default to disabled unless explicitly forced
        if self.is_production and "DOCS_ENABLED" not in os.environ:
            self.docs_enabled = False

        # 6. Production Startup Validation
        self.validate_production_constraints()

    @property
    def is_production(self) -> bool:
        """Determines if the platform is running in production mode."""
        return self.environment in ("production", "prod")

    def validate_production_constraints(self) -> None:
        """
        Enforces strict security checks on production startup.
        Fails fast if insecure defaults or missing secrets are detected.
        """
        if self.is_production and self.auth_enabled:
            # Disallow insecure default development secret
            if "dev-insecure-secret" in self.jwt_secret or len(self.jwt_secret) < 32:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "JWT_SECRET must be set to a cryptographically strong secret of at least 32 characters in production."
                )

            # Prevent wildcard CORS when credentials are enabled
            if self.cors_allow_credentials and "*" in self.cors_allowed_origins:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "CORS allowed origins cannot contain wildcard '*' when credentials are enabled."
                )

        if self.is_production and not self.redis_url:
            import logging
            logging.getLogger(__name__).warning(
                "PRODUCTION NOTICE: REDIS_URL is not set. Distributed rate limiting and shared token revocation "
                "will operate in local in-memory mode per application instance."
            )


# Global singleton security configuration
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Returns or initializes the active SecurityConfig singleton."""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


def set_security_config(config: Optional[SecurityConfig]) -> None:
    """Overrides or resets security configuration (useful in testing)."""
    global _security_config
    _security_config = config
