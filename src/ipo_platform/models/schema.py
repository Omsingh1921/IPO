"""
Data schema specifications for Indian IPO Research & Data Analysis Platform.
Implements Schema Version 1.0 per docs/ipo-data-schema.md.
Provides robust dataclass representations with helper methods for serialization/deserialization.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from .enums import (
    SegmentEnum,
    IPOStatusEnum,
    ListingStatusEnum,
    PeriodTypeEnum,
    DataTypeEnum,
    SourceTypeEnum,
    ScenarioStatusEnum,
    InvestorTypeEnum,
    RiskCategoryEnum,
    RiskSeverityEnum,
    PerformanceEventTypeEnum,
    ObjectsDisclosureStatusEnum,
    DataCompletenessEnum,
    SourceVerificationEnum,
)


@dataclass
class ProvenanceEnvelope:
    """Envelope wrapping numerical datapoints with source attribution and metadata."""

    value: Any  # Union[float, int, str] e.g. 750.00 or "Not available"
    unit: Optional[str] = None
    currency: Optional[str] = "INR"
    data_type: DataTypeEnum = DataTypeEnum.REPORTED
    source: str = "Unspecified"
    source_date: Optional[str] = None
    retrieval_timestamp: Optional[str] = None


@dataclass
class SourceRecord:
    """Standardized provenance object attached to primary research data."""

    source_name: str
    source_type: SourceTypeEnum
    source_url: Optional[str] = None
    publication_date: Optional[str] = None
    retrieval_timestamp: Optional[str] = None
    page_or_section: Optional[str] = None
    data_type: DataTypeEnum = DataTypeEnum.REPORTED
    notes: Optional[str] = None


@dataclass
class IPOEntity:
    """Central master entity identifying the offering."""

    ipo_id: str
    company_name: str
    company_legal_name: str
    ticker_symbol: str
    isin: str
    segment: SegmentEnum
    sector: str
    industry: str


@dataclass
class IPOStatus:
    """Lifecycle status and data reconciliation timestamps."""

    status: IPOStatusEnum
    research_date: str
    research_time: str
    data_cutoff: str
    open_date: str
    close_date: str
    listing_date: str
    listing_status: ListingStatusEnum


@dataclass
class IssueStructure:
    """Offering mechanics and capital structure."""

    issue_size: ProvenanceEnvelope
    fresh_issue_amount: ProvenanceEnvelope
    ofs_amount: ProvenanceEnvelope
    fresh_issue_percentage: ProvenanceEnvelope
    ofs_percentage: ProvenanceEnvelope
    face_value: ProvenanceEnvelope
    price_band_low: ProvenanceEnvelope
    price_band_high: ProvenanceEnvelope
    issue_price: ProvenanceEnvelope
    lot_size: ProvenanceEnvelope
    minimum_investment: ProvenanceEnvelope
    employee_reservation: Optional[ProvenanceEnvelope] = None
    shareholder_reservation: Optional[ProvenanceEnvelope] = None
    other_reservation: Optional[ProvenanceEnvelope] = None


@dataclass
class ObjectOfIssue:
    """Deployment item for fresh issue proceeds."""

    purpose: str
    amount: float
    source: str
    source_date: str
    percentage_of_fresh_issue: Optional[float] = None
    disclosure_status: ObjectsDisclosureStatusEnum = ObjectsDisclosureStatusEnum.DISCLOSED


@dataclass
class FinancialRecord:
    """Historical restated financial statement entry for a given period."""

    financial_period: str
    period_type: PeriodTypeEnum
    revenue: Optional[ProvenanceEnvelope] = None
    revenue_growth: Optional[ProvenanceEnvelope] = None
    EBITDA: Optional[ProvenanceEnvelope] = None
    EBITDA_margin: Optional[ProvenanceEnvelope] = None
    PAT: Optional[ProvenanceEnvelope] = None
    PAT_growth: Optional[ProvenanceEnvelope] = None
    EPS: Optional[ProvenanceEnvelope] = None
    book_value_per_share: Optional[ProvenanceEnvelope] = None
    ROE: Optional[ProvenanceEnvelope] = None
    ROCE: Optional[ProvenanceEnvelope] = None
    total_debt: Optional[ProvenanceEnvelope] = None
    net_debt: Optional[ProvenanceEnvelope] = None
    debt_equity: Optional[ProvenanceEnvelope] = None
    operating_cash_flow: Optional[ProvenanceEnvelope] = None
    investing_cash_flow: Optional[ProvenanceEnvelope] = None
    financing_cash_flow: Optional[ProvenanceEnvelope] = None
    free_cash_flow: Optional[ProvenanceEnvelope] = None


@dataclass
class ValuationData:
    """Valuation parameters and relative multiples."""

    reference_price: float
    reference_eps: float
    issue_pe: ProvenanceEnvelope
    valuation_method: str
    valuation_source: str
    valuation_date: str
    issue_pb: Optional[ProvenanceEnvelope] = None
    industry_pe: Optional[ProvenanceEnvelope] = None
    industry_pb: Optional[ProvenanceEnvelope] = None
    peer_average_pe: Optional[ProvenanceEnvelope] = None
    peer_average_pb: Optional[ProvenanceEnvelope] = None
    reference_book_value_per_share: Optional[float] = None


@dataclass
class Scenario40Percent:
    """Container evaluating the conditional +40% upside scenario hypothesis.

    Standardized Formula Rules:
      target_price = reference_price * 1.40
      required_price_movement = 40.00
    Prohibited Fields: probability_of_40_percent, guaranteed_return, recommendation, buy_signal.
    """

    reference_price: float
    target_price: float
    supporting_factors: List[str]
    contradictory_factors: List[str]
    scenario_status: ScenarioStatusEnum
    scenario_methodology: str
    scenario_data_timestamp: str
    required_price_movement: float = 40.00
    target_pe: Optional[float] = None
    target_pb: Optional[float] = None


@dataclass
class SubscriptionCategory:
    """Subscription record for a single investor category."""

    shares_offered: int
    shares_bid: int
    subscription_multiple: float
    source: str
    source_date: str
    retrieval_timestamp: str


@dataclass
class AnchorInvestor:
    """Factual record of institutional anchor placement."""

    investor_name: str
    investor_type: InvestorTypeEnum
    allocation_amount: float
    allocation_shares: int
    allocation_percentage: float
    source: str
    source_date: str


@dataclass
class AnchorData:
    """Aggregate anchor placement metrics and participant list."""

    anchor_allocation: float
    anchor_price: float
    anchor_investor_count: int
    anchor_allocation_percentage: float
    lock_in_30_day: str
    lock_in_90_day: str
    anchor_investors: List[AnchorInvestor] = field(default_factory=list)


@dataclass
class GMPData:
    """Indicative Grey Market Premium log."""

    gmp_value: float
    gmp_percentage: float
    gmp_date: str
    gmp_time: str
    reference_price: float
    implied_price: float
    source: str
    source_type: SourceTypeEnum = SourceTypeEnum.UNOFFICIAL_GMP


@dataclass
class PeerCompany:
    """Listed direct peer benchmark company."""

    company_name: str
    ticker: str
    source: str
    source_date: str
    market_cap: Optional[float] = None
    revenue: Optional[float] = None
    PAT: Optional[float] = None
    EPS: Optional[float] = None
    PE: Optional[float] = None
    PB: Optional[float] = None
    ROE: Optional[float] = None
    ROCE: Optional[float] = None
    debt_equity: Optional[float] = None


@dataclass
class RiskRecord:
    """Disclosed risk factor from statutory offer document."""

    risk_category: RiskCategoryEnum
    risk_description: str
    severity: RiskSeverityEnum
    source: str
    source_date: str


@dataclass
class DataQuality:
    """Data quality and completeness assessment."""

    completeness_status: DataCompletenessEnum
    source_verification_status: SourceVerificationEnum
    last_verified: str
    missing_fields: List[str] = field(default_factory=list)
    conflicting_data: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class HistoricalIPO:
    """Post-listing outcome metrics (Strictly segregated from Pre-IPO data)."""

    historical_ipo: bool = False
    ipo_year: Optional[int] = None
    listing_price: Any = "Not available"
    listing_day_close: Any = "Not available"
    listing_day_high: Any = "Not available"
    listing_day_low: Any = "Not available"
    listing_day_return: Any = "Not available"
    post_listing_7d_return: Any = "Not available"
    post_listing_30d_return: Any = "Not available"
    post_listing_90d_return: Any = "Not available"
    post_listing_180d_return: Any = "Not available"
    post_listing_1y_return: Any = "Not available"
    max_upside_from_issue_price: Any = "Not available"
    max_drawdown_from_issue_price: Any = "Not available"


@dataclass
class PerformanceEvent:
    """Longitudinal event stream record for post-listing performance backtesting."""

    event_date: str
    event_type: PerformanceEventTypeEnum
    reference_price: float
    market_price: float
    return_percentage: float
    days_from_listing: int
    reached_40_percent_target: bool
    source: str


@dataclass
class MasterIPORecord:
    """Root container representing complete structured IPO dataset."""

    ipo_entity: IPOEntity
    ipo_status: IPOStatus
    issue_structure: IssueStructure
    valuation_data: ValuationData
    scenario_40_percent: Scenario40Percent
    data_quality: DataQuality
    schema_version: str = "1.0"
    objects_of_issue: List[ObjectOfIssue] = field(default_factory=list)
    financial_data: List[FinancialRecord] = field(default_factory=list)
    subscription_data: Dict[str, SubscriptionCategory] = field(default_factory=dict)
    anchor_data: Optional[AnchorData] = None
    gmp_data: Optional[GMPData] = None
    peer_companies: List[PeerCompany] = field(default_factory=list)
    risk_data: List[RiskRecord] = field(default_factory=list)
    sources: List[SourceRecord] = field(default_factory=list)
    historical_ipo: Optional[HistoricalIPO] = None
    performance_events: List[PerformanceEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass structure to python dictionary."""
        return asdict(self)
