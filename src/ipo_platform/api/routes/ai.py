"""
Google Gemini AI Routes for Indian IPO Platform.
Exposes endpoints for generating AI Investment Thesis and interactive IPO Copilot Q&A.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from ipo_platform.api.dependencies import get_query_service
from ipo_platform.security.rate_limiter import rate_limit
from ipo_platform.security.rbac import Role, require_role
from ipo_platform.services.gemini_service import GeminiService, get_gemini_service
from ipo_platform.services.query_service import IPOQueryService

router = APIRouter(prefix="", tags=["AI Intelligence"])


class AskQuestionRequest(BaseModel):
    """Payload for asking Gemini Copilot a question about an IPO."""
    question: str = Field(..., min_length=2, max_length=1000, description="User question about the IPO")
    chat_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous messages in chat")


class AskQuestionResponse(BaseModel):
    """Response returned by Gemini Copilot."""
    ipo_id: str
    company_name: str
    question: str
    answer: str
    ai_provider: str


class AIStatusResponse(BaseModel):
    """Status of Google Gemini integration."""
    configured: bool
    model: str
    provider: str = "Google Gemini"
    message: str


@router.get(
    "/ai/status",
    response_model=AIStatusResponse,
    summary="Get Google Gemini AI Integration Status",
    dependencies=[Depends(rate_limit())],
)
def get_ai_status(
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> AIStatusResponse:
    """Checks whether Google Gemini API is configured with a valid key."""
    configured = gemini_service.is_configured
    msg = (
        f"Google Gemini is active using model '{gemini_service.model}'"
        if configured
        else "Gemini API key is not configured. Running with high-precision algorithmic fallback."
    )
    return AIStatusResponse(
        configured=configured,
        model=gemini_service.model,
        provider="Google Gemini",
        message=msg,
    )


@router.get(
    "/ipos/{ipo_id}/ai-thesis",
    summary="Get Google Gemini AI Investment Thesis",
    description="Generates an institutional Bull/Bear case and investment verdict using Google Gemini.",
    dependencies=[Depends(require_role(Role.READ_ONLY)), Depends(rate_limit())],
)
@router.post(
    "/ipos/{ipo_id}/ai-thesis",
    summary="Generate Google Gemini AI Investment Thesis",
    dependencies=[Depends(require_role(Role.READ_ONLY)), Depends(rate_limit())],
)
def get_or_generate_ai_thesis(
    ipo_id: str = Path(..., description="Unique IPO identifier or ticker symbol"),
    query_service: IPOQueryService = Depends(get_query_service),
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> Dict[str, Any]:
    """Generates an institutional AI thesis for the target IPO."""
    record = query_service.get_ipo_details(ipo_id)
    if not record:
        record = query_service.get_ipo_by_slug(ipo_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IPO '{ipo_id}' not found in platform database",
        )

    thesis = gemini_service.generate_ipo_thesis(record)
    thesis["ipo_id"] = record.ipo_entity.ipo_id if record.ipo_entity else ipo_id
    thesis["company_name"] = record.ipo_entity.company_name if record.ipo_entity else ipo_id
    return thesis


@router.post(
    "/ipos/{ipo_id}/ai-ask",
    response_model=AskQuestionResponse,
    summary="Ask Google Gemini Copilot About This IPO",
    description="Answers investor questions (English or Hinglish) using factual IPO data.",
    dependencies=[Depends(require_role(Role.READ_ONLY)), Depends(rate_limit())],
)
def ask_gemini_copilot(
    payload: AskQuestionRequest,
    ipo_id: str = Path(..., description="Unique IPO identifier or ticker symbol"),
    query_service: IPOQueryService = Depends(get_query_service),
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> AskQuestionResponse:
    """Answers an investor question using Gemini Copilot."""
    record = query_service.get_ipo_details(ipo_id)
    if not record:
        record = query_service.get_ipo_by_slug(ipo_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IPO '{ipo_id}' not found in platform database",
        )

    comp_name = record.ipo_entity.company_name if record.ipo_entity else ipo_id
    answer = gemini_service.ask_ipo_copilot(
        record=record,
        question=payload.question,
        chat_history=payload.chat_history,
    )

    provider_name = (
        f"Google Gemini ({gemini_service.model})"
        if gemini_service.is_configured
        else "Algorithmic Quantitative Fallback"
    )

    return AskQuestionResponse(
        ipo_id=record.ipo_entity.ipo_id if record.ipo_entity else ipo_id,
        company_name=comp_name,
        question=payload.question,
        answer=answer,
        ai_provider=provider_name,
    )
