"""
Security Package for Indian IPO Platform (Phase 10 - Stage 5).
Exposes path sanitization, atomic file writers, defensive input validation guards,
enterprise authentication, RBAC, rate limiting, and HTTP security middleware.
"""

from ipo_platform.security.auth import (
    AuthenticatedPrincipal,
    TokenRevocationStore,
    TokenRevokedError,
    create_access_token,
    decode_access_token,
    get_current_principal,
    get_optional_principal,
    get_revocation_store,
    set_revocation_store,
    validate_api_key,
)
from ipo_platform.security.config import (
    SecurityConfig,
    get_security_config,
    set_security_config,
)
from ipo_platform.security.hardening import (
    EnvironmentValidationError,
    InputValidationError,
    PathTraversalError,
    SecurityError,
    safe_write_file,
    sanitize_filename,
    sanitize_path,
    validate_env_var,
    validate_output_directory,
    validate_safe_command_args,
)
from ipo_platform.security.middleware import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from ipo_platform.security.rate_limiter import (
    BaseRateLimiter,
    InMemoryRateLimiter,
    RateLimitResult,
    get_rate_limiter,
    rate_limit,
    set_rate_limiter,
)
from ipo_platform.security.rbac import (
    Role,
    has_sufficient_role,
    require_role,
)

__all__ = [
    # Hardening & sanitization
    "SecurityError",
    "PathTraversalError",
    "EnvironmentValidationError",
    "InputValidationError",
    "sanitize_path",
    "sanitize_filename",
    "validate_output_directory",
    "safe_write_file",
    "validate_env_var",
    "validate_safe_command_args",
    # Configuration
    "SecurityConfig",
    "get_security_config",
    "set_security_config",
    # RBAC
    "Role",
    "has_sufficient_role",
    "require_role",
    # Authentication
    "AuthenticatedPrincipal",
    "TokenRevocationStore",
    "create_access_token",
    "decode_access_token",
    "validate_api_key",
    "get_current_principal",
    "get_optional_principal",
    "get_revocation_store",
    "set_revocation_store",
    # Rate Limiting
    "rate_limit",
    "BaseRateLimiter",
    "InMemoryRateLimiter",
    "RateLimitResult",
    "get_rate_limiter",
    "set_rate_limiter",
    # Middleware
    "SecurityHeadersMiddleware",
    "RequestSizeLimitMiddleware",
]
