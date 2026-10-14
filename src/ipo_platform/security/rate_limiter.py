"""
Rate Limiting & Abuse Prevention Engine (Phase 10 - Stage 5).
Provides sliding-window rate limiting with in-memory thread-safe tracking,
optional Redis backend, fail-safe degradation, and FastAPI dependencies.
"""

from collections import deque
from dataclasses import dataclass
import ipaddress
import logging
import threading
import time
from typing import Callable, Deque, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, Response, status

from ipo_platform.observability.metrics import default_registry
from ipo_platform.security.auth import AuthenticatedPrincipal, get_optional_principal
from ipo_platform.security.config import SecurityConfig, get_security_config

logger = logging.getLogger(__name__)

# Metrics tracking rate-limiting actions
_RATE_LIMIT_EXCEEDED_COUNTER = default_registry.counter(
    "rate_limit_exceeded_total", "Count of rejected requests due to rate limits"
)


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate limit check."""
    allowed: bool
    remaining: int
    limit: int
    reset_seconds: int


class BaseRateLimiter:
    """Abstract interface for rate limiting implementations."""

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        raise NotImplementedError

    def reset(self) -> None:
        """Clears all rate limit state (primarily for test isolation)."""
        pass


class InMemoryRateLimiter(BaseRateLimiter):
    """
    Thread-safe, sliding-window in-memory rate limiter using timestamps deque.
    Auto-prunes expired access timestamps.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: Dict[str, Deque[float]] = {}

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            if key not in self._windows:
                self._windows[key] = deque()

            timestamps = self._windows[key]

            # Prune timestamps outside current window
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            current_count = len(timestamps)
            if current_count >= limit:
                # Calculate remaining seconds until oldest request expires
                oldest = timestamps[0]
                reset_seconds = max(1, int(oldest + window_seconds - now))
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=limit,
                    reset_seconds=reset_seconds,
                )

            # Record current request timestamp
            timestamps.append(now)
            remaining = limit - (current_count + 1)
            return RateLimitResult(
                allowed=True,
                remaining=max(0, remaining),
                limit=limit,
                reset_seconds=window_seconds,
            )

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


class RedisRateLimiter(BaseRateLimiter):
    """
    Distributed sliding-window rate limiter backed by Redis.
    Fails safely to an internal InMemoryRateLimiter if Redis is unavailable or errors out.
    """

    def __init__(self, redis_url: str, fallback: InMemoryRateLimiter) -> None:
        self._redis_url = redis_url
        self._fallback = fallback
        self._client = None
        self._init_failed = False
        self._last_retry_time = 0.0
        self._retry_interval_seconds = 30.0
        self._init_client()

    def _init_client(self) -> None:
        try:
            import redis
            self._client = redis.Redis.from_url(self._redis_url, socket_timeout=1.0)
            self._client.ping()
            self._init_failed = False
        except Exception as exc:
            logger.warning("Redis rate limiter unavailable (%s); falling back to in-memory: %s", self._redis_url, exc)
            self._client = None
            self._init_failed = True
            self._last_retry_time = time.time()

    def is_available(self) -> bool:
        """Checks if Redis client is available; attempts reconnecting if retry interval has elapsed."""
        if self._client is None or self._init_failed:
            now = time.time()
            if now - self._last_retry_time > self._retry_interval_seconds:
                self._last_retry_time = now
                self._init_client()
        return not self._init_failed

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        if not self.is_available():
            return self._fallback.check(key, limit, window_seconds)

        try:
            now = time.time()
            window_start = now - window_seconds
            pipe = self._client.pipeline()
            redis_key = f"rl:{key}"

            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # Count current
            pipe.zcard(redis_key)
            # Add current member
            pipe.zadd(redis_key, {str(now): now})
            # Set TTL
            pipe.expire(redis_key, window_seconds + 5)
            results = pipe.execute()

            current_count = results[1]
            if current_count >= limit:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=limit,
                    reset_seconds=window_seconds,
                )

            remaining = max(0, limit - (current_count + 1))
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                limit=limit,
                reset_seconds=window_seconds,
            )
        except Exception as exc:
            logger.warning("Redis operation failed in rate limiter; gracefully falling back to in-memory: %s", exc)
            self._init_failed = True
            self._last_retry_time = time.time()
            return self._fallback.check(key, limit, window_seconds)

    def reset(self) -> None:
        self._fallback.reset()
        if self._client:
            try:
                # Only clear rate-limiting keys
                for k in self._client.scan_iter("rl:*"):
                    self._client.delete(k)
            except Exception:
                pass


# Global singleton instance
_in_memory_limiter = InMemoryRateLimiter()
_active_limiter: Optional[BaseRateLimiter] = None


def get_rate_limiter(config: Optional[SecurityConfig] = None) -> BaseRateLimiter:
    """Returns the configured rate limiter singleton."""
    global _active_limiter
    if _active_limiter is None:
        sec_cfg = config or get_security_config()
        if sec_cfg.redis_url:
            _active_limiter = RedisRateLimiter(sec_cfg.redis_url, fallback=_in_memory_limiter)
        else:
            _active_limiter = _in_memory_limiter
    return _active_limiter


def set_rate_limiter(limiter: Optional[BaseRateLimiter]) -> None:
    """Overrides the active rate limiter (useful for deterministic test isolation)."""
    global _active_limiter
    _active_limiter = limiter


def _is_peer_in_trusted_proxies(peer_ip: str, trusted_proxies: List[str]) -> bool:
    """
    Checks if peer_ip matches any trusted proxy IP address or CIDR network range.
    Safely handles invalid IP addresses or CIDR notations.
    """
    if not peer_ip or not trusted_proxies:
        return False
    try:
        peer_addr = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False

    for trusted_entry in trusted_proxies:
        entry = trusted_entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if peer_addr in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if peer_addr == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


def get_client_identifier(
    request: Request,
    principal: Optional[AuthenticatedPrincipal],
    config: Optional[SecurityConfig] = None,
) -> str:
    """
    Derives an abuse-prevention identity key:
    - If authenticated: uses principal ID
    - If unauthenticated: inspects peer IP.
      Only trusts 'X-Forwarded-For' if proxy headers are explicitly trusted
      or peer IP matches trusted_proxies (IP or CIDR). Arbitrary client-supplied
      forwarding headers from untrusted peers are ignored to prevent IP spoofing.
    """
    if principal and principal.principal_id:
        return f"principal:{principal.principal_id}"

    sec_cfg = config or get_security_config()
    peer_ip = request.client.host if (request.client and request.client.host) else "unknown_client"

    # Only trust X-Forwarded-For if proxy headers are explicitly enabled or peer is a trusted proxy
    is_trusted_proxy = sec_cfg.trust_proxy_headers or _is_peer_in_trusted_proxies(
        peer_ip, sec_cfg.trusted_proxies
    )

    if is_trusted_proxy:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Client IP is the first entry in X-Forwarded-For chain
            client_ip = forwarded_for.split(",")[0].strip()
            return f"ip:{client_ip}"

    return f"ip:{peer_ip}"


def rate_limit(
    max_requests: Optional[int] = None,
    window_seconds: int = 60,
    endpoint_tag: Optional[str] = None,
    is_expensive: bool = False,
) -> Callable:
    """
    FastAPI dependency applying rate limiting to a route.
    If max_requests is None, uses default from SecurityConfig based on caller auth status.
    Supports explicit fail-closed policy for expensive endpoints during Redis outages.
    Returns:
        Callable dependency that raises 429 if rate limit is exceeded.
    """
    def _rate_limiter_dependency(
        request: Request,
        response: Response,
        principal: Optional[AuthenticatedPrincipal] = Depends(get_optional_principal),
        config: SecurityConfig = Depends(get_security_config),
    ) -> None:
        if not config.rate_limit_enabled:
            return

        tag = endpoint_tag or request.url.path
        limiter = get_rate_limiter(config)

        # Check explicit fail-closed policy for expensive endpoints during Redis outage
        if is_expensive and config.rate_limit_fail_closed_expensive:
            if isinstance(limiter, RedisRateLimiter) and not limiter.is_available():
                logger.error("Rate limiter rejecting expensive request on %s due to Redis outage (fail-closed policy)", tag)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable: rate limiting backend unavailable for high-cost endpoint",
                    headers={"Retry-After": "30"},
                )

        # Determine effective limit
        if max_requests is not None:
            limit = max_requests
        elif principal is not None:
            limit = config.rate_limit_authenticated_rpm
        else:
            limit = config.rate_limit_unauthenticated_rpm

        # Derive rate limit key safely using verified proxy policy
        client_id = get_client_identifier(request, principal, config)
        key = f"{tag}:{client_id}"

        result = limiter.check(key, limit=limit, window_seconds=window_seconds)

        # Set standard rate-limiting headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_seconds)

        if not result.allowed:
            _RATE_LIMIT_EXCEEDED_COUNTER.inc(tags={"endpoint": tag})
            logger.warning("Rate limit exceeded for %s on %s (limit: %d/%ds)", client_id, tag, limit, window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too Many Requests: rate limit exceeded. Please retry later.",
                headers={
                    "Retry-After": str(result.reset_seconds),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_seconds),
                },
            )

    return _rate_limiter_dependency
