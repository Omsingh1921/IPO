"""
Pydantic Request and Response DTO Schemas for Indian IPO Recommendation API (Phase 10 - Stage 4).
Provides strict validation, serialization contracts, and OpenAPI documentation schemas.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Enums
# ==========================================

class RecommendationCategoryEnum(str, Enum):
    AVOID = "AVOID"
    NEUTRAL = "NEUTRAL"
    SUBSCRIBE = "SUBSCRIBE"
    STRONG_SUBSCRIBE = "STRONG_SUBSCRIBE"


class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class RiskProfileEnum(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class HealthStatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


# ==========================================
# Generic & Error Schemas
# ==========================================

class ErrorResponse(BaseModel):
    """Standardized RFC 7807-inspired API Error Schema."""
    error: str = Field(..., description="High-level error classification")
    detail: str = Field(..., description="Detailed human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of error occurrence"
    )
    path: Optional[str] = Field(None, description="Request URL path where error occurred")

    model_config = ConfigDict(extra="forbid")


# ==========================================
# Health Check Schemas
# ==========================================

class HealthCheckDetail(BaseModel):
    """Result of an individual subsystem health probe."""
    status: HealthStatusEnum = Field(..., description="Subsystem health status")
    message: str = Field("", description="Diagnostic message or status summary")
    duration_ms: float = Field(0.0, description="Probe execution latency in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry details")


class HealthResponse(BaseModel):
    """Consolidated platform system health status."""
    status: HealthStatusEnum = Field(..., description="Overall platform operational status")
    healthy_count: int = Field(..., description="Number of operational probes")
    degraded_count: int = Field(..., description="Number of degraded probes")
    unhealthy_count: int = Field(..., description="Number of failing probes")
    total_duration_ms: float = Field(..., description="Total time taken for all diagnostic probes in ms")
    timestamp: str = Field(..., description="UTC ISO-8601 execution timestamp")
    checks: Dict[str, HealthCheckDetail] = Field(..., description="Individual subsystem probe results")


class UpstreamFeedProbeDetail(BaseModel):
    """Diagnostic latency and status detail for an individual external upstream feed."""
    name: str = Field(..., description="Feed display name (e.g. BSE India, NSE India, InvestorGain GMP)")
    status: str = Field(..., description="Feed health status (healthy, degraded, unhealthy)")
    latency_ms: float = Field(..., description="Round-trip HTTP probe latency in milliseconds")
    http_code: Optional[int] = Field(None, description="Upstream HTTP status code (e.g. 200, 403, 503)")
    items_count: int = Field(0, description="Count of live offerings or records detected")
    last_check: str = Field(..., description="Formatted timestamp of last probe check")
    error: Optional[str] = Field(None, description="Detailed error or exception reason if unhealthy")


class UpstreamFeedsHealthResponse(BaseModel):
    """Consolidated real-time latency and status across all external upstream feeds."""
    overall_status: str = Field(..., description="Consolidated status (healthy, degraded, unhealthy)")
    timestamp: str = Field(..., description="UTC ISO-8601 execution timestamp")
    total_probe_duration_ms: float = Field(..., description="Duration of concurrent probing in milliseconds")
    feeds: Dict[str, UpstreamFeedProbeDetail] = Field(..., description="Probes per feed key (bse, nse, gmp)")



# ==========================================
# IPO Information Schemas
# ==========================================

class IPOListItem(BaseModel):
    """Summary representation of an IPO offering in catalog listings."""
    ipo_id: str = Field(..., description="Unique alphanumeric identifier of the IPO")
    company_name: str = Field(..., description="Primary legal or operating company name")
    status: Optional[str] = Field(None, description="Current offering lifecycle status")
    sector: Optional[str] = Field(None, description="Industrial sector classification")
    issue_size_cr: Optional[float] = Field(None, description="Total offering size in INR Crores")
    price_band: Optional[str] = Field(None, description="Offering price band range (e.g., 480 - 500)")
    open_date: Optional[str] = Field(None, description="Bidding commencement date")
    close_date: Optional[str] = Field(None, description="Bidding conclusion date")
    allotment_date: Optional[str] = Field(None, description="Basis of allotment finalization date")
    listing_date: Optional[str] = Field(None, description="Scheduled exchange listing date")
    subscription_times: Optional[float] = Field(None, description="Total subscription multiple in times (e.g., 12.5x)")
    subscription_summary: Optional[str] = Field(None, description="Subscription breakdown by category (e.g., QIB: 12.5x, Retail: 4.5x)")
    qib_subscription: Optional[float] = Field(None, description="QIB category subscription multiple in times")
    nii_subscription: Optional[float] = Field(None, description="NII category subscription multiple in times")
    retail_subscription: Optional[float] = Field(None, description="Retail category subscription multiple in times")
    employee_subscription: Optional[float] = Field(None, description="Employee category subscription multiple in times")
    subscription_breakdown: Optional[Dict[str, float]] = Field(None, description="Granular category subscription multiples map")
    gmp_percentage: Optional[float] = Field(None, description="Latest Grey Market Premium percentage")
    segment: Optional[str] = Field(None, description="Offering segment, e.g. Mainboard or SME")
    ticker_symbol: Optional[str] = Field(None, description="Exchange ticker or symbol")


class IPOListResponse(BaseModel):
    """Paginated collection of IPO offerings."""
    total: int = Field(..., description="Total count of matching IPO records")
    skip: int = Field(0, description="Offset count for pagination")
    limit: int = Field(50, description="Page size limit")
    items: List[IPOListItem] = Field(default_factory=list, description="Array of IPO summaries")


class IPODetailResponse(BaseModel):
    """Complete detail specification of an individual IPO."""
    ipo_id: str = Field(..., description="Unique alphanumeric identifier of the IPO")
    company_name: str = Field(..., description="Primary legal or operating company name")
    record: Dict[str, Any] = Field(..., description="Full canonical MasterIPORecord data structure")


# ==========================================
# Recommendation Engine Schemas
# ==========================================

class GMPOverrideDto(BaseModel):
    """Optional manual Grey Market Premium quote override."""
    gmp_value: float = Field(..., ge=-100000.0, le=100000.0, description="Absolute GMP rupee value per share")
    gmp_percentage: float = Field(..., ge=-100.0, le=10000.0, description="Relative GMP percentage premium over issue price")
    reference_price: Optional[float] = Field(None, ge=0.0, le=1000000.0, description="Upper price band issue price reference")
    implied_price: Optional[float] = Field(None, ge=0.0, le=1000000.0, description="Expected listing price (reference + gmp)")
    gmp_date: Optional[str] = Field(None, max_length=30, description="Date of GMP quote")
    source: Optional[str] = Field("Manual API Override", max_length=100, description="Attributed data source")


class FactorScoreDto(BaseModel):
    """Individual factor evaluation score breakdown."""
    name: str = Field(..., description="Name of the evaluated quantitative factor")
    raw_value: Optional[float] = Field(None, description="Raw numerical value extracted from filing/market")
    score: float = Field(..., description="Normalized factor score between 0.0 and 100.0")
    weight: float = Field(..., description="Portfolio allocation weight assigned to factor")
    weighted_score: float = Field(..., description="Score contribution = score * weight")
    description: Optional[str] = Field(None, description="Descriptive notes or provenance warning")
    is_available: bool = Field(True, description="Whether factor was available or defaulted")


class EvaluateRecommendationRequest(BaseModel):
    """Request payload for quantitative recommendation evaluation."""
    ipo_id: Optional[str] = Field(
        None, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-\.]+$", description="Existing IPO ID in database to evaluate"
    )
    record: Optional[Dict[str, Any]] = Field(None, description="Raw MasterIPORecord JSON payload to evaluate")
    gmp_override: Optional[GMPOverrideDto] = Field(None, description="Optional manual GMP quote override")

    @field_validator("record")
    @classmethod
    def validate_payload_presence(cls, v: Optional[Dict[str, Any]], info) -> Optional[Dict[str, Any]]:
        return v


class EvaluateRecommendationResponse(BaseModel):
    """Quantitative recommendation evaluation result."""
    ipo_id: str = Field(..., description="Unique identifier of evaluated IPO")
    company_name: str = Field(..., description="Company name")
    recommendation: RecommendationCategoryEnum = Field(..., description="Algorithmic recommendation verdict")
    composite_score: float = Field(..., description="Normalized composite score between 0.0 and 100.0")
    confidence_score: float = Field(..., description="Data completeness confidence rating between 0.0 and 1.0")
    risk_level: RiskLevelEnum = Field(..., description="Risk tier classification")
    factor_scores: Dict[str, FactorScoreDto] = Field(..., description="Breakdown of all 9 factor scores")
    strengths: List[str] = Field(default_factory=list, description="Primary positive drivers identified")
    risks: List[str] = Field(default_factory=list, description="Primary risk factors or red flags")
    veto_applied: Optional[str] = Field(None, description="Fatal red-flag veto if triggered")
    summary_rationale: str = Field(..., description="Deterministic investment rationale narrative")
    evaluation_timestamp: str = Field(..., description="UTC ISO-8601 evaluation timestamp")


# ==========================================
# Validation Engine Schemas
# ==========================================

class CategoryPerformanceDto(BaseModel):
    """Empirical performance breakdown for a recommendation category."""
    category: str = Field(..., description="Category name (STRONG_SUBSCRIBE, SUBSCRIBE, NEUTRAL, AVOID)")
    total_count: int = Field(..., description="Total historical IPOs assigned this category")
    winning_count: int = Field(..., description="Number of profitable outcomes (listing return > 0)")
    losing_count: int = Field(..., description="Number of unprofitable outcomes (listing return <= 0)")
    win_rate: Optional[float] = Field(None, description="Percentage of profitable outcomes")
    average_return: Optional[float] = Field(None, description="Mean listing day return percentage")
    median_return: Optional[float] = Field(None, description="Median listing day return percentage")
    max_return: Optional[float] = Field(None, description="Maximum listing day return percentage")
    min_return: Optional[float] = Field(None, description="Minimum listing day return percentage")
    success_rate: Optional[float] = Field(None, description="Category-specific validation success rate %")


class ValidateRecommendationRequest(BaseModel):
    """Request payload to execute historical validation backtest."""
    records: Optional[List[Dict[str, Any]]] = Field(
        None, max_length=500, description="List of historical MasterIPORecord JSON dicts with listing outcomes (max 500)"
    )
    strong_subscribe_success_min_return: float = Field(
        15.0, ge=-100.0, le=1000.0, description="Minimum listing return % to consider STRONG_SUBSCRIBE valid (default 15.0%)"
    )
    subscribe_success_min_return: float = Field(
        5.0, ge=-100.0, le=1000.0, description="Minimum listing return % to consider SUBSCRIBE valid (default 5.0%)"
    )
    avoid_success_max_return: float = Field(
        5.0, ge=-100.0, le=1000.0, description="Maximum listing return % to consider AVOID valid (default <= 5.0%)"
    )


class ValidateRecommendationResponse(BaseModel):
    """Empirical recommendation validation report."""
    total_evaluated: int = Field(..., description="Total records processed")
    historical_cohort_size: int = Field(..., description="Records containing valid post-listing return data")
    overall_accuracy: float = Field(..., description="Overall predictive accuracy percentage (0-100)")
    precision: Optional[float] = Field(None, description="Precision score for actionable buy signals")
    recall: Optional[float] = Field(None, description="Recall rate for identifying winning IPOs")
    f1_score: Optional[float] = Field(None, description="Harmonic mean of precision and recall")
    win_rate: Optional[float] = Field(None, description="Aggregate cohort win rate percentage")
    average_return: Optional[float] = Field(None, description="Mean listing day return across cohort")
    strong_subscribe_accuracy: Optional[float] = Field(None, description="STRONG_SUBSCRIBE accuracy %")
    avoid_accuracy: Optional[float] = Field(None, description="AVOID accuracy %")
    recommendation_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution count per recommendation category"
    )
    category_breakdown: Dict[str, CategoryPerformanceDto] = Field(
        default_factory=dict, description="Performance breakdown per recommendation category"
    )
    generated_at: str = Field(..., description="UTC ISO-8601 generation timestamp")
    validation_notes: List[str] = Field(default_factory=list, description="Diagnostic observations and notes")


# ==========================================
# Portfolio Engine Schemas
# ==========================================

class RecommendationInputDto(BaseModel):
    """Lightweight recommendation structure for portfolio allocation."""
    ipo_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-\.]+$", description="Unique IPO identifier")
    company_name: str = Field(..., min_length=1, max_length=200, description="Company name")
    recommendation: RecommendationCategoryEnum = Field(..., description="Recommendation category")
    composite_score: float = Field(..., ge=0.0, le=100.0, description="Engine composite score (0-100)")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Data completeness confidence")
    risk_level: RiskLevelEnum = Field(default=RiskLevelEnum.MEDIUM, description="Risk tier")
    sector: str = Field(default="General", max_length=100, description="Industry sector for concentration management")
    expected_return: Optional[float] = Field(None, ge=-100.0, le=10000.0, description="Optional custom expected listing return %")


class AllocatePortfolioRequest(BaseModel):
    """Request payload for portfolio capital allocation."""
    available_capital: float = Field(
        ..., gt=0.0, le=1e12, description="Total capital available for allocation in INR (must be > 0 and <= 1e12)"
    )
    risk_profile: RiskProfileEnum = Field(
        default=RiskProfileEnum.MODERATE, description="Investor risk tolerance profile"
    )
    recommendations: Optional[List[RecommendationInputDto]] = Field(
        None, max_length=100, description="List of pre-evaluated recommendation objects (max 100)"
    )
    records: Optional[List[Dict[str, Any]]] = Field(
        None, max_length=100, description="List of raw MasterIPORecord JSON dictionaries to evaluate and allocate (max 100)"
    )

    @field_validator("available_capital")
    @classmethod
    def validate_positive_capital(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("Available capital must be strictly greater than 0")
        return v


class CapitalAllocationDto(BaseModel):
    """Individual IPO position allocation."""
    ipo_id: str = Field(..., description="IPO identifier")
    company_name: str = Field(..., description="Company name")
    recommendation: str = Field(..., description="Recommendation category")
    risk_level: str = Field(..., description="Risk tier")
    sector: str = Field(..., description="Sector")
    allocated_amount: float = Field(..., description="Capital allocated in INR")
    allocation_percentage: float = Field(..., description="Allocation as percentage of available capital")
    portfolio_weight: float = Field(..., description="Weight relative to total deployed capital")
    expected_return: float = Field(..., description="Modeled expected return %")
    expected_risk: float = Field(..., description="Modeled standard deviation risk %")
    rationale: str = Field(..., description="Allocation rationale and constraints applied")


class AllocatePortfolioResponse(BaseModel):
    """Complete portfolio recommendation and risk diagnostics."""
    total_capital: float = Field(..., description="Total input capital in INR")
    total_allocated_capital: float = Field(..., description="Sum of capital allocated to IPOs in INR")
    unallocated_cash: float = Field(..., description="Remaining liquidity preserved in cash in INR")
    total_allocation_percentage: float = Field(..., description="Aggregate percentage of capital deployed")
    risk_profile: str = Field(..., description="Applied risk profile (CONSERVATIVE, MODERATE, AGGRESSIVE)")
    allocations: List[CapitalAllocationDto] = Field(default_factory=list, description="Allocated positions")
    sector_allocations: Dict[str, float] = Field(default_factory=dict, description="Sector concentration %")
    portfolio_risk_score: float = Field(..., description="Composite portfolio risk index (0-100)")
    concentration_risk: float = Field(..., description="Normalized Herfindahl-Hirschman Index (0-100)")
    exposure_risk: float = Field(..., description="Capital exposure risk index (0-100)")
    portfolio_risk_category: str = Field(..., description="Aggregated risk tier (LOW, MODERATE, HIGH, VERY_HIGH)")
    expected_return: float = Field(..., description="Portfolio-level expected return %")
    expected_risk: float = Field(..., description="Portfolio-level volatility risk %")
    sharpe_score: float = Field(..., description="Risk-adjusted Sharpe-like efficiency ratio")
    diversification_notes: List[str] = Field(default_factory=list, description="Diversification actions taken")
    generated_at: str = Field(..., description="UTC ISO-8601 generation timestamp")


# ==========================================
# Metrics Schemas
# ==========================================

class MetricsResponse(BaseModel):
    """Instantaneous snapshot of platform telemetry counters, gauges, and timers."""
    timestamp: float = Field(..., description="Unix epoch timestamp of snapshot")
    counters: List[Dict[str, Any]] = Field(default_factory=list, description="Registered monotonic counters")
    gauges: List[Dict[str, Any]] = Field(default_factory=list, description="Instantaneous gauge instruments")
    timers: List[Dict[str, Any]] = Field(default_factory=list, description="Latency timers and histograms")


# ==========================================
# Wishlist & Post-Listing History Schemas
# ==========================================

class WishlistHistoryItemDto(BaseModel):
    """Post-listing track record for wishlisted IPO offering."""
    id: Optional[int] = Field(None, description="Unique history record ID")
    ipo_id: str = Field(..., description="Unique IPO identifier")
    company_name: str = Field(..., description="Security / Issuer company name")
    segment: Optional[str] = Field(None, description="Market segment (Mainboard / SME)")
    issue_price: Optional[float] = Field(None, description="Final offer / issue price in INR")
    listing_price: Optional[float] = Field(None, description="Actual exchange opening/listing price in INR")
    listing_gain_pct: Optional[float] = Field(None, description="Listing day return percentage ((listing - issue)/issue * 100)")
    listing_date: Optional[str] = Field(None, description="Exchange listing date (YYYY-MM-DD)")
    listing_day_close: Optional[float] = Field(None, description="Listing day closing price in INR")
    status: str = Field(default="Listed", description="Listing status")
    notes: Optional[str] = Field(None, description="User notes or observation tags")
    wishlist_added_at: Optional[str] = Field(None, description="Timestamp when bookmarked in wishlist")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class WishlistHistoryListResponse(BaseModel):
    """List response for wishlist post-listing history."""
    total: int = Field(..., description="Total count of post-listing history records")
    items: List[WishlistHistoryItemDto] = Field(default_factory=list, description="Array of history records")


class UpdateListingPriceRequest(BaseModel):
    """Payload to record or update actual listing price for a wishlisted IPO."""
    listing_price: float = Field(..., gt=0, description="Actual listing price in INR")
    issue_price: Optional[float] = Field(None, gt=0, description="Optional override for issue price")
    listing_day_close: Optional[float] = Field(None, gt=0, description="Optional listing day close price in INR")
    listing_date: Optional[str] = Field(None, description="Optional listing date (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional observation notes")

