"""
Portfolio Strategy & Capital Allocation Route Handlers (Phase 10 - Stage 5).
Exposes POST /portfolio/allocate endpoint delegating directly to IPOPortfolioEngine.
Requires OPERATOR role or higher. Protected by rate limiting.
"""

from typing import List, Optional, Tuple, Union
from fastapi import APIRouter, Depends, HTTPException, status

from ipo_platform.api.dependencies import (
    get_portfolio_engine,
    get_query_service,
    get_recommendation_engine,
)
from ipo_platform.api.schemas import (
    AllocatePortfolioRequest,
    AllocatePortfolioResponse,
    CapitalAllocationDto,
    RecommendationInputDto,
)
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.portfolio.allocation_models import RiskProfile
from ipo_platform.portfolio.portfolio_engine import IPOPortfolioEngine
from ipo_platform.recommendation.recommendation_engine import IPORecommendationEngine
from ipo_platform.recommendation.recommendation_result import RecommendationResult
from ipo_platform.recommendation.scoring_models import RecommendationCategory, RiskLevel
from ipo_platform.security.rate_limiter import rate_limit
from ipo_platform.security.rbac import Role, require_role
from ipo_platform.services.query_service import IPOQueryService

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


def _dto_to_recommendation_result(dto: RecommendationInputDto) -> RecommendationResult:
    """Constructs a RecommendationResult aggregate from RecommendationInputDto."""
    return RecommendationResult(
        ipo_id=dto.ipo_id,
        company_name=dto.company_name,
        recommendation=RecommendationCategory(dto.recommendation.value),
        composite_score=dto.composite_score,
        confidence_score=dto.confidence_score,
        risk_level=RiskLevel(dto.risk_level.value),
        factor_scores={},
        strengths=[],
        risks=[],
        summary_rationale="Input recommendation specification",
    )


@router.post(
    "/allocate",
    response_model=AllocatePortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Allocate Portfolio Capital Across IPOs",
    description="Allocates liquidity according to risk profile constraints (max 35% single IPO, max 40% sector). Requires OPERATOR role.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit(endpoint_tag="/portfolio/allocate"))],
)
def allocate_portfolio(
    payload: AllocatePortfolioRequest,
    portfolio_engine: IPOPortfolioEngine = Depends(get_portfolio_engine),
    recommendation_engine: IPORecommendationEngine = Depends(get_recommendation_engine),
    query_service: IPOQueryService = Depends(get_query_service),
) -> AllocatePortfolioResponse:
    """Executes quantitative capital allocation and portfolio risk optimization."""
    # Enforce positive capital
    if payload.available_capital <= 0.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Available capital must be strictly greater than 0",
        )

    risk_prof = RiskProfile(payload.risk_profile.value)
    items: List[Tuple[RecommendationResult, str]] = []

    # Case 1: Direct recommendations provided
    if payload.recommendations and len(payload.recommendations) > 0:
        for dto in payload.recommendations:
            rec_res = _dto_to_recommendation_result(dto)
            items.append((rec_res, dto.sector or "General"))

    # Case 2: Raw records provided -> evaluate them first
    elif payload.records and len(payload.records) > 0:
        for idx, rec_dict in enumerate(payload.records):
            try:
                rec_obj = JSONIngestor.from_dict(rec_dict)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Record at index {idx} failed to parse: {exc}",
                )
            rec_eval = recommendation_engine.evaluate(rec_obj)
            sec = (
                getattr(rec_obj.ipo_entity, "sector", "General")
                if rec_obj.ipo_entity
                else "General"
            )
            items.append((rec_eval, sec or "General"))

    # Case 3: Neither provided -> check active database IPOs
    else:
        active_records = query_service.list_active_ipos(limit=50)
        for rec_obj in active_records:
            rec_eval = recommendation_engine.evaluate(rec_obj)
            sec = (
                getattr(rec_obj.ipo_entity, "sector", "General")
                if rec_obj.ipo_entity
                else "General"
            )
            items.append((rec_eval, sec or "General"))

    # Execute portfolio allocation
    portfolio_rec = portfolio_engine.allocate_portfolio(
        recommendations=items,
        available_capital=payload.available_capital,
        risk_profile=risk_prof,
    )
    p_dict = portfolio_rec.to_dict()

    alloc_dtos = [
        CapitalAllocationDto(
            ipo_id=a["ipo_id"],
            company_name=a["company_name"],
            recommendation=a["recommendation"],
            risk_level=a["risk_level"],
            sector=a["sector"],
            allocated_amount=a["allocated_amount"],
            allocation_percentage=a["allocation_percentage"],
            portfolio_weight=a["portfolio_weight"],
            expected_return=a["expected_return"],
            expected_risk=a["expected_risk"],
            rationale=a["rationale"],
        )
        for a in p_dict.get("allocations", [])
    ]

    return AllocatePortfolioResponse(
        total_capital=p_dict["total_capital"],
        total_allocated_capital=p_dict["total_allocated_capital"],
        unallocated_cash=p_dict["unallocated_cash"],
        total_allocation_percentage=p_dict["total_allocation_percentage"],
        risk_profile=p_dict["risk_profile"],
        allocations=alloc_dtos,
        sector_allocations=p_dict.get("sector_allocations", {}),
        portfolio_risk_score=p_dict["portfolio_risk_score"],
        concentration_risk=p_dict["concentration_risk"],
        exposure_risk=p_dict["exposure_risk"],
        portfolio_risk_category=p_dict["portfolio_risk_category"],
        expected_return=p_dict["expected_return"],
        expected_risk=p_dict["expected_risk"],
        sharpe_score=p_dict["sharpe_score"],
        diversification_notes=p_dict.get("diversification_notes", []),
        generated_at=p_dict.get("generated_at", ""),
    )
