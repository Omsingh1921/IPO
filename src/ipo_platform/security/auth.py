"""
Authentication Engine & Principal Management for Indian IPO Platform API (Phase 10 - Stage 5).
Implements JWT tokens, API Keys with constant-time verification, and FastAPI dependencies.
Never logs raw tokens, passwords, or secrets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import secrets
import threading
import time
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    PyJWTError,
)

from ipo_platform.observability.metrics import default_registry
from ipo_platform.security.config import SecurityConfig, get_security_config
from ipo_platform.security.rbac import Role

logger = logging.getLogger(__name__)

# Metrics for security auditing
_AUTH_FAILURE_COUNTER = default_registry.counter(
    "auth_failures_total", "Total count of authentication failures"
)
_AUTH_SUCCESS_COUNTER = default_registry.counter(
    "auth_success_total", "Total count of successful authentications"
)


class TokenRevokedError(PyJWTError):
    """Raised when a validly signed JWT has been explicitly revoked."""
    pass


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Immutable representation of an authenticated user or service principal."""
    principal_id: str
    role: Role
    auth_method: str  # "jwt", "api_key", or "dev_bypass"
    claims: Dict[str, Any] = field(default_factory=dict)

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_operator(self) -> bool:
        return self.role in (Role.OPERATOR, Role.ADMIN)


class TokenRevocationStore:
    """
    Manages active token revocations and blocklists.
    Supports in-memory tracking with optional distributed Redis storage.
    Defines safe fallback behavior when Redis is unavailable.

    Operational Limitation in Fail-Open / In-Memory Mode:
    When Redis is not configured or unavailable, token revocations are stored
    exclusively in the local in-memory store of the active application process.
    In multi-pod / multi-instance deployments, an in-memory revocation performed
    on Pod A will NOT propagate to Pod B. For multi-replica production deployments,
    REDIS_URL must be configured to ensure cross-pod revocation synchronization.
    """

    def __init__(self, config: Optional[SecurityConfig] = None) -> None:
        self.config = config or get_security_config()
        self._lock = threading.Lock()
        self._revoked_jtis: Dict[str, float] = {}  # jti -> expires_at
        self._revoked_users: Dict[str, float] = {}  # principal_id -> revoked_before_timestamp
        self._redis_client = None
        self._redis_failed = False
        self._last_retry_time = 0.0
        self._retry_interval_seconds = 30.0
        self._init_redis()

    def _init_redis(self) -> None:
        if self.config.redis_url:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(
                    self.config.redis_url,
                    socket_timeout=1.0,
                    decode_responses=True,
                )
                self._redis_client.ping()
                self._redis_failed = False
            except Exception as exc:
                logger.warning("Redis token revocation store unavailable (%s): %s", self.config.redis_url, exc)
                self._redis_client = None
                self._redis_failed = True
                self._last_retry_time = time.time()

    def _check_or_reconnect_redis(self) -> None:
        """Attempts reconnecting to Redis if the retry interval has elapsed."""
        if (self._redis_client is None or self._redis_failed) and self.config.redis_url:
            now = time.time()
            if now - self._last_retry_time > self._retry_interval_seconds:
                self._last_retry_time = now
                self._init_redis()

    def revoke_token(self, jti: str, expires_at: float) -> None:
        """Revokes a specific token by JTI until its expiration timestamp."""
        now = time.time()
        ttl = max(1, int(expires_at - now))
        with self._lock:
            self._revoked_jtis[jti] = expires_at

        self._check_or_reconnect_redis()
        if self._redis_client and not self._redis_failed:
            try:
                self._redis_client.setex(f"jwt:revoked:{jti}", ttl, "1")
            except Exception as exc:
                logger.warning("Failed to store token revocation in Redis: %s", exc)
                self._redis_failed = True
                self._last_retry_time = time.time()

    def revoke_user_tokens(self, principal_id: str) -> None:
        """Revokes all tokens issued for a specific user prior to the current timestamp."""
        now = time.time()
        with self._lock:
            self._revoked_users[principal_id] = now

        self._check_or_reconnect_redis()
        if self._redis_client and not self._redis_failed:
            try:
                self._redis_client.setex(f"jwt:user_revoked_at:{principal_id}", 86400 * 7, str(now))
            except Exception as exc:
                logger.warning("Failed to store user revocation in Redis: %s", exc)
                self._redis_failed = True
                self._last_retry_time = time.time()

    def is_revoked(self, jti: Optional[str], principal_id: str, issued_at: Optional[Any]) -> bool:
        """
        Checks whether token or user has been revoked.
        If Redis fails, follows jwt_revocation_fail_closed policy.
        """
        now = time.time()

        # Check local in-memory store
        with self._lock:
            # Prune expired local entries
            expired_keys = [k for k, exp in self._revoked_jtis.items() if exp <= now]
            for k in expired_keys:
                del self._revoked_jtis[k]

            if jti and jti in self._revoked_jtis:
                return True

            if principal_id in self._revoked_users:
                revoked_before = self._revoked_users[principal_id]
                if issued_at is not None and float(issued_at) <= revoked_before:
                    return True

        # Check Redis if configured
        self._check_or_reconnect_redis()
        if self._redis_client and not self._redis_failed:
            try:
                if jti and self._redis_client.get(f"jwt:revoked:{jti}"):
                    return True
                user_rev = self._redis_client.get(f"jwt:user_revoked_at:{principal_id}")
                if user_rev and issued_at is not None and float(issued_at) <= float(user_rev):
                    return True
            except Exception as exc:
                logger.warning("Redis query failed in revocation store: %s", exc)
                self._redis_failed = True
                self._last_retry_time = time.time()
                if self.config.jwt_revocation_fail_closed:
                    raise PyJWTError("Token verification service unavailable")

        return False

    def reset(self) -> None:
        with self._lock:
            self._revoked_jtis.clear()
            self._revoked_users.clear()


_global_revocation_store: Optional[TokenRevocationStore] = None


def get_revocation_store(config: Optional[SecurityConfig] = None) -> TokenRevocationStore:
    """Returns or creates the TokenRevocationStore singleton."""
    global _global_revocation_store
    if _global_revocation_store is None:
        _global_revocation_store = TokenRevocationStore(config)
    return _global_revocation_store


def set_revocation_store(store: Optional[TokenRevocationStore]) -> None:
    """Overrides the revocation store (useful in test isolation)."""
    global _global_revocation_store
    _global_revocation_store = store


def create_access_token(
    principal_id: str,
    role: Role,
    expires_delta: Optional[timedelta] = None,
    custom_claims: Optional[Dict[str, Any]] = None,
    config: Optional[SecurityConfig] = None,
) -> str:
    """
    Issues a cryptographically signed JSON Web Token (JWT).
    Includes expiration, issuer, audience, jti, and standard claims.
    """
    sec_cfg = config or get_security_config()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=sec_cfg.jwt_access_token_expire_minutes)

    now_ts = now.timestamp()
    payload: Dict[str, Any] = {
        "sub": principal_id,
        "role": role.value,
        "iat": now_ts,
        "nbf": now_ts,
        "exp": int(expire.timestamp()),
        "iss": sec_cfg.jwt_issuer,
        "aud": sec_cfg.jwt_audience,
        "jti": secrets.token_urlsafe(16),
    }

    if custom_claims:
        for k, v in custom_claims.items():
            payload[k] = v

    token = jwt.encode(
        payload,
        sec_cfg.jwt_secret,
        algorithm=sec_cfg.jwt_algorithm,
    )
    return token


def decode_access_token(
    token: str,
    config: Optional[SecurityConfig] = None,
) -> AuthenticatedPrincipal:
    """
    Decodes and validates a JWT token.
    Enforces signature verification, expiration, issuer, audience, and revocation checks.
    Raises PyJWTError subclasses on invalid tokens.
    """
    sec_cfg = config or get_security_config()

    # Reject non-string or whitespace tokens
    if not token or not isinstance(token, str) or not token.strip():
        raise PyJWTError("Token string is empty or invalid")

    payload = jwt.decode(
        token.strip(),
        sec_cfg.jwt_secret,
        algorithms=[sec_cfg.jwt_algorithm],
        issuer=sec_cfg.jwt_issuer,
        audience=sec_cfg.jwt_audience,
        options={
            "require": ["sub", "exp", "iat", "role"],
            "verify_exp": True,
            "verify_iat": True,
            "verify_nbf": True,
        },
    )

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise PyJWTError("Token claim 'sub' is missing or invalid")

    # Check revocation status if enabled
    if sec_cfg.jwt_revocation_enabled:
        store = get_revocation_store(sec_cfg)
        jti = payload.get("jti")
        iat = payload.get("iat")
        if store.is_revoked(jti, sub, iat):
            raise TokenRevokedError("Authentication token has been revoked")

    role_str = payload.get("role", "READ_ONLY")
    role = Role.from_str(str(role_str))

    return AuthenticatedPrincipal(
        principal_id=sub,
        role=role,
        auth_method="jwt",
        claims=payload,
    )


def validate_api_key(
    api_key: str,
    config: Optional[SecurityConfig] = None,
) -> Optional[AuthenticatedPrincipal]:
    """
    Validates an API Key using constant-time comparison against configured keys.
    Returns AuthenticatedPrincipal if matched, None otherwise.
    """
    sec_cfg = config or get_security_config()
    if not api_key or not sec_cfg.api_keys:
        return None

    # Constant-time comparison over configured keys
    for configured_key, role_str in sec_cfg.api_keys.items():
        if secrets.compare_digest(api_key.strip(), configured_key):
            role = Role.from_str(role_str)
            # Mask key for identifier (first 4 chars + ellipsis)
            masked_id = f"apikey-{api_key[:4]}..." if len(api_key) >= 4 else "apikey-anon"
            return AuthenticatedPrincipal(
                principal_id=masked_id,
                role=role,
                auth_method="api_key",
                claims={"api_key_role": role.value},
            )

    return None


def get_current_principal(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    config: SecurityConfig = Depends(get_security_config),
) -> AuthenticatedPrincipal:
    """
    FastAPI dependency extracting and authenticating caller credentials.
    Supports:
    1. HTTP Bearer JWT token in 'Authorization' header
    2. API Key in 'X-API-Key' header
    Raises:
        HTTPException 401 if unauthenticated or credentials invalid.
    """
    # 1. Check if authentication is disabled globally (e.g. in test fixture or dev config)
    if not config.auth_enabled:
        return AuthenticatedPrincipal(
            principal_id="dev-bypass",
            role=Role.ADMIN,
            auth_method="dev_bypass",
            claims={"auth_disabled": True},
        )

    # 2. Check X-API-Key header
    if x_api_key:
        principal = validate_api_key(x_api_key, config=config)
        if principal:
            _AUTH_SUCCESS_COUNTER.inc(tags={"method": "api_key", "role": principal.role.value})
            return principal
        else:
            logger.warning("Authentication failure: invalid API key provided")
            _AUTH_FAILURE_COUNTER.inc(tags={"method": "api_key", "reason": "invalid_key"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # 3. Check Authorization Bearer token header
    if authorization:
        parts = authorization.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Authentication failure: malformed Authorization header")
            _AUTH_FAILURE_COUNTER.inc(tags={"method": "jwt", "reason": "malformed_header"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]
        try:
            principal = decode_access_token(token, config=config)
            _AUTH_SUCCESS_COUNTER.inc(tags={"method": "jwt", "role": principal.role.value})
            return principal
        except ExpiredSignatureError:
            logger.warning("Authentication failure: JWT token has expired")
            _AUTH_FAILURE_COUNTER.inc(tags={"method": "jwt", "reason": "expired"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token has expired\""},
            )
        except TokenRevokedError:
            logger.warning("Authentication failure: JWT token has been revoked")
            _AUTH_FAILURE_COUNTER.inc(tags={"method": "jwt", "reason": "revoked"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has been revoked",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token has been revoked\""},
            )
        except (InvalidSignatureError, InvalidIssuerError, InvalidAudienceError, PyJWTError) as exc:
            logger.warning("Authentication failure: invalid JWT token: %s", type(exc).__name__)
            _AUTH_FAILURE_COUNTER.inc(tags={"method": "jwt", "reason": "invalid_token"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )

    # 4. No credentials provided
    logger.warning("Authentication failure: missing credentials")
    _AUTH_FAILURE_COUNTER.inc(tags={"method": "none", "reason": "missing_credentials"})
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: missing Bearer token or X-API-Key",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_optional_principal(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    config: SecurityConfig = Depends(get_security_config),
) -> Optional[AuthenticatedPrincipal]:
    """
    FastAPI dependency for public or semi-public endpoints where authentication is optional.
    Returns AuthenticatedPrincipal if valid credentials are provided, None otherwise.
    """
    if not authorization and not x_api_key:
        return None

    try:
        return get_current_principal(authorization=authorization, x_api_key=x_api_key, config=config)
    except HTTPException:
        return None
