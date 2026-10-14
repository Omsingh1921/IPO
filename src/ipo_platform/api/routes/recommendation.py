"""
Recommendation Intelligence & Validation Route Handlers (Phase 10 - Stage 5).
Exposes POST /recommendation/evaluate and POST /recommendation/validate endpoints.
Requires OPERATOR role or higher. Protected by granular rate limiting.
Delegates directly to IPORecommendationEngine and RecommendationValidationEngine.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ipo_platform.api.dependencies import (
    get_query_service,
    get_recommendation_engine,
    get_validation_engine,
)
from ipo_platform.api.schemas import (
    CategoryPerformanceDto,
    EvaluateRecommendationRequest,
    EvaluateRecommendationResponse,
    FactorScoreDto,
    GMPOverrideDto,
    RecommendationCategoryEnum,
    RiskLevelEnum,
    ValidateRecommendationRequest,
    ValidateRecommendationResponse,
)
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.schema import GMPData, MasterIPORecord
from ipo_platform.recommendation.recommendation_engine import IPORecommendationEngine
from ipo_platform.recommendation.validation import RecommendationValidationEngine
from ipo_platform.security.rate_limiter import rate_limit
from ipo_platform.security.rbac import Role, require_role
from ipo_platform.services.query_service import IPOQueryService

router = APIRouter(prefix="/recommendation", tags=["Recommendation"])


def _convert_gmp_override(dto: Optional[GMPOverrideDto]) -> Optional[GMPData]:
    """Helper to convert API GMPOverrideDto to domain GMPData."""
    if dto is None:
        return None
    return GMPData(
        gmp_value=dto.gmp_value,
        gmp_percentage=dto.gmp_percentage,
        gmp_date=dto.gmp_date or "",
        gmp_time="",
        reference_price=dto.reference_price or 0.0,
        implied_price=dto.implied_price or (
            (dto.reference_price or 0.0) + dto.gmp_value
        ),
        source=dto.source or "Manual API Override",
    )


@router.post(
    "/evaluate",
    response_model=EvaluateRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate IPO Recommendation",
    description="Calculates 9-factor scores, composite score (0-100), risk tier, and recommendation for an IPO. Requires OPERATOR role.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit(endpoint_tag="/recommendation/evaluate"))],
)
def evaluate_recommendation(
    payload: EvaluateRecommendationRequest,
    engine: IPORecommendationEngine = Depends(get_recommendation_engine),
    query_service: IPOQueryService = Depends(get_query_service),
) -> EvaluateRecommendationResponse:
    """Evaluates an IPO either from a provided JSON record or an existing database ipo_id."""
    record: Optional[MasterIPORecord] = None

    if payload.record is not None:
        try:
            record = JSONIngestor.from_dict(payload.record)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse MasterIPORecord: {exc}",
            )
    elif payload.ipo_id is not None:
        record = query_service.get_ipo_details(payload.ipo_id)
        if record is None:
            record = query_service.get_ipo_by_slug(payload.ipo_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"IPO with id '{payload.ipo_id}' not found in platform database",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'record' (JSON dict) or 'ipo_id' must be specified in request body",
        )

    gmp_override = _convert_gmp_override(payload.gmp_override)
    rec_result = engine.evaluate(record, gmp_override=gmp_override)
    data = rec_result.to_dict()

    factor_scores_dto = {
        name: FactorScoreDto(
            name=fs.get("name", name),
            raw_value=fs.get("raw_value"),
            score=fs.get("normalized_score", fs.get("score", 0.0)),
            weight=fs.get("weight", 0.0),
            weighted_score=fs.get("weighted_score", 0.0),
            description=fs.get("description"),
            is_available=fs.get("is_available", True),
        )
        for name, fs in data.get("factor_scores", {}).items()
    }

    return EvaluateRecommendationResponse(
        ipo_id=data["ipo_id"],
        company_name=data["company_name"],
        recommendation=RecommendationCategoryEnum(data["recommendation"]),
        composite_score=data["composite_score"],
        confidence_score=data["confidence_score"],
        risk_level=RiskLevelEnum(data["risk_level"]),
        factor_scores=factor_scores_dto,
        strengths=data.get("strengths", []),
        risks=data.get("risks", []),
        veto_applied=data.get("veto_applied"),
        summary_rationale=data.get("summary_rationale", ""),
        evaluation_timestamp=data.get("evaluation_timestamp", ""),
    )


@router.post(
    "/validate",
    response_model=ValidateRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Recommendations Against Historical Outcomes",
    description="Backtests recommendation accuracy, win rate, precision, recall, and category gains on historical IPOs. Requires OPERATOR role.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit(max_requests=20, window_seconds=60, endpoint_tag="/recommendation/validate", is_expensive=True))],
)
def validate_recommendations(
    payload: ValidateRecommendationRequest,
    validation_engine: RecommendationValidationEngine = Depends(get_validation_engine),
    query_service: IPOQueryService = Depends(get_query_service),
) -> ValidateRecommendationResponse:
    """Executes empirical backtesting and validation across a cohort of historical IPOs."""
    records: List[MasterIPORecord] = []

    if payload.records and len(payload.records) > 0:
        for idx, rec_dict in enumerate(payload.records):
            try:
                rec_obj = JSONIngestor.from_dict(rec_dict)
                records.append(rec_obj)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Record at index {idx} failed to parse: {exc}",
                )
    else:
        # Fallback: Query historical records from database
        db_records = query_service.list_active_ipos(limit=500)
        # Filter for historical records
        records = [r for r in db_records if r.historical_ipo and r.historical_ipo.historical_ipo]

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No historical records provided or available in the platform for validation.",
        )

    # Configure custom return benchmark thresholds if provided
    engine_to_use = RecommendationValidationEngine(
        engine=validation_engine.engine,
        strong_subscribe_success_min_return=payload.strong_subscribe_success_min_return,
        subscribe_success_min_return=payload.subscribe_success_min_return,
        avoid_success_max_return=payload.avoid_success_max_return,
    )

    report = engine_to_use.validate_cohort(records)
    rep_dict = report.to_dict()

    cat_perf_dto = {}
    for cat_name, cat_data in rep_dict.get("category_breakdown", {}).items():
        cat_perf_dto[cat_name] = CategoryPerformanceDto(
            category=cat_data["category"],
            total_count=cat_data["total_count"],
            winning_count=cat_data["winning_count"],
            losing_count=cat_data["losing_count"],
            win_rate=cat_data.get("win_rate"),
            average_return=cat_data.get("average_return"),
            median_return=cat_data.get("median_return"),
            max_return=cat_data.get("max_return"),
            min_return=cat_data.get("min_return"),
            success_rate=cat_data.get("success_rate"),
        )

    return ValidateRecommendationResponse(
        total_evaluated=rep_dict["total_evaluated"],
        historical_cohort_size=rep_dict["historical_cohort_size"],
        overall_accuracy=rep_dict["overall_accuracy"],
        precision=rep_dict.get("precision"),
        recall=rep_dict.get("recall"),
        f1_score=rep_dict.get("f1_score"),
        win_rate=rep_dict.get("win_rate"),
        average_return=rep_dict.get("average_return"),
        strong_subscribe_accuracy=rep_dict.get("strong_subscribe_accuracy"),
        avoid_accuracy=rep_dict.get("avoid_accuracy"),
        recommendation_distribution=rep_dict.get("recommendation_distribution", {}),
        category_breakdown=cat_perf_dto,
        generated_at=rep_dict.get("generated_at", ""),
        validation_notes=rep_dict.get("validation_notes", []),
    )
