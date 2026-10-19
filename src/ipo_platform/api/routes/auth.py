"""
Authentication Route Handler for Indian IPO Platform API.
Provides endpoints for user sign-in, token generation, and principal validation.
"""

import os
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ipo_platform.security.auth import (
    AuthenticatedPrincipal,
    create_access_token,
    get_current_principal,
    validate_api_key,
)
from ipo_platform.security.config import SecurityConfig, get_security_config
from ipo_platform.security.rbac import Role

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    key_or_password: str = Field(..., description="Admin Master Key, Password, or API Key")
    username: Optional[str] = Field(None, description="Optional username (defaults to personal-admin)")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_minutes: int


@router.post("/login", response_model=LoginResponse, summary="Sign in to platform")
def login(
    req: LoginRequest,
    config: SecurityConfig = Depends(get_security_config),
) -> LoginResponse:
    """
    Authenticates a personal user or administrator and issues a signed JWT Bearer token.
    """
    credential = req.key_or_password.strip()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential must not be empty",
        )

    # 1. Check if credential is a valid API key
    principal = validate_api_key(credential, config=config)
    role = principal.role if principal else None

    # 2. Check if credential matches ADMIN_PASSWORD environment variable
    admin_pwd = os.getenv("ADMIN_PASSWORD", "").strip()
    if not role and admin_pwd and secrets.compare_digest(credential, admin_pwd):
        role = Role.ADMIN

    # 3. Development fallback keys (disabled in production)
    if not role and not config.is_production:
        dev_map = {
            "key-admin-789": Role.ADMIN,
            "key-operator-456": Role.OPERATOR,
            "key-readonly-123": Role.READ_ONLY,
        }
        role = dev_map.get(credential)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access key or credentials",
        )

    # Issue JWT Token
    token = create_access_token(
        principal_id=req.username or "personal-admin",
        role=role,
        config=config,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=role.value,
        expires_in_minutes=config.jwt_access_token_expire_minutes,
    )


@router.get("/me", summary="Check current authenticated principal")
def get_me(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
):
    """Returns details of the currently authenticated principal."""
    return {
        "authenticated": True,
        "principal_id": principal.principal_id,
        "role": principal.role.value,
        "auth_method": principal.auth_method,
    }
