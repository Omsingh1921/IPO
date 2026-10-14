"""
Role-Based Access Control (RBAC) Architecture (Phase 10 - Stage 5).
Defines operational roles, hierarchical permissions, and FastAPI authorization dependencies.
"""

from enum import Enum
import logging
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """
    Standard platform roles with hierarchical permissions:
    - READ_ONLY: Read-only access to IPO catalog, details, evaluation results, health.
    - OPERATOR: All READ_ONLY operations + evaluate recommendations, validate backtests, allocate portfolios.
    - ADMIN: All OPERATOR operations + access system metrics, configure security, administrative actions.
    """
    READ_ONLY = "READ_ONLY"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"

    @classmethod
    def from_str(cls, role_str: str) -> "Role":
        """Safely parses a string into a Role enum, defaulting to READ_ONLY on unknown input."""
        try:
            return cls(role_str.upper().strip())
        except (ValueError, AttributeError):
            return cls.READ_ONLY


# Explicit role hierarchy numeric weights
_ROLE_HIERARCHY = {
    Role.READ_ONLY: 10,
    Role.OPERATOR: 20,
    Role.ADMIN: 30,
}


def has_sufficient_role(principal_role: Role, required_role: Role) -> bool:
    """
    Determines if principal_role meets or exceeds the required_role in the hierarchy.
    Returns True if principal has adequate permission, False otherwise.
    """
    user_weight = _ROLE_HIERARCHY.get(principal_role, 0)
    required_weight = _ROLE_HIERARCHY.get(required_role, 999)
    return user_weight >= required_weight


def require_role(required_role: Role) -> Callable:
    """
    FastAPI dependency factory enforcing minimum role requirement.
    Raises:
        HTTPException 401 if unauthenticated (handled by get_current_principal).
        HTTPException 403 if authenticated principal has insufficient role.
    """
    # Lazy import to avoid circular dependencies between auth and rbac
    from ipo_platform.security.auth import get_current_principal, AuthenticatedPrincipal

    def _role_checker(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if not has_sufficient_role(principal.role, required_role):
            logger.warning(
                "Authorization failure: principal '%s' with role '%s' attempted to access endpoint requiring '%s'",
                principal.principal_id,
                principal.role.value,
                required_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions",
            )
        return principal

    return _role_checker
