"""
SQLAlchemy 2.0 ORM Entity Models for Indian IPO Platform.
Implements 14 physical tables with version_id OCC, VARCHAR enum safety, and ON DELETE RESTRICT FKs.
"""

from typing import Optional, List
from sqlalchemy import (
    BigInteger,
    Integer,
    Numeric,
    String,
    Text,
    Date,
    Time,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from .base import Base


class SourceModel(Base):
    """Centralized provenance source registry (Table: sources)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    retrieval_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    page_or_section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Reported")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_source_type_date", "source_type", "publication_date"),
    )


class IPOMasterModel(Base):
    """Master IPO Entity (Table: ipo_master). Features version_id OCC."""

    __tablename__ = "ipo_master"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker_symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12), unique=True, nullable=True)
    segment: Mapped[str] = mapped_column(String(64), nullable=False)
    sector: Mapped[str] = mapped_column(String(128), nullable=False)
    industry: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    research_date: Mapped[Date] = mapped_column(Date, nullable=False)
    research_time: Mapped[Time] = mapped_column(Time, nullable=False)
    data_cutoff: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    open_date: Mapped[Date] = mapped_column(Date, nullable=False)
    close_date: Mapped[Date] = mapped_column(Date, nullable=False)
    listing_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    listing_status: Mapped[str] = mapped_column(String(64), nullable=False, default="Pre-Listing")
    issue_size: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    fresh_issue_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0.00)
    ofs_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0.00)
    fresh_issue_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    ofs_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    face_value: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    price_band_low: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    price_band_high: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    issue_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_investment: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    employee_reservation: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    shareholder_reservation: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    other_reservation: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deleted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __mapper_args__ = {"version_id_col": version_id}

    __table_args__ = (
        Index("idx_ipo_status_dates", "status", "open_date", "close_date"),
        Index("idx_ipo_segment_sector", "segment", "sector"),
        Index("idx_ipo_listing_date", "listing_date"),
    )


class ObjectOfIssueModel(Base):
    """Fresh issue capital deployment utilization (Table: ipo_objects_of_issue)."""

    __tablename__ = "ipo_objects_of_issue"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    purpose_type: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose_description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    percentage_of_fresh_issue: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    disclosure_status: Mapped[str] = mapped_column(String(64), nullable=False, default="Disclosed")
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_obj_ipo_purpose", "ipo_id", "purpose_type"),
    )


class FinancialModel(Base):
    """Multi-period restated financial statements (Table: financials)."""

    __tablename__ = "financials"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    financial_period: Mapped[str] = mapped_column(String(32), nullable=False)
    period_type: Mapped[str] = mapped_column(String(64), nullable=False)
    revenue: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    revenue_growth: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    EBITDA: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    EBITDA_margin: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    PAT: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    PAT_growth: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    EPS: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    book_value_per_share: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    ROE: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    ROCE: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    total_debt: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    net_debt: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    debt_equity: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    operating_cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    investing_cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    financing_cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    free_cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Reported")
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("ipo_id", "financial_period", name="uq_fin_ipo_period"),
        Index("idx_fin_period_type", "ipo_id", "period_type", "financial_period"),
    )


class ValuationModel(Base):
    """Valuation benchmarks and peer relative multiples (Table: valuation)."""

    __tablename__ = "valuation"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    issue_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reference_eps: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    reference_book_value_per_share: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    issue_pe: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    issue_pb: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    industry_pe: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    industry_pb: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    peer_average_pe: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    peer_average_pb: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    valuation_method: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    valuation_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    valuation_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Calculated")
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_val_ipo", "ipo_id"),
    )


class SubscriptionModel(Base):
    """Time-series exchange order book snapshots (Table: subscription)."""

    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    subscription_date: Mapped[Date] = mapped_column(Date, nullable=False)
    subscription_day: Mapped[str] = mapped_column(String(16), nullable=False)
    QIB_shares_offered: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    QIB_shares_bid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    QIB_subscription_multiple: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    NII_total_shares_offered: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    NII_total_shares_bid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    NII_total_subscription_multiple: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    sHNI_shares_offered: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sHNI_shares_bid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sHNI_subscription_multiple: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    bHNI_shares_offered: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    bHNI_shares_bid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    bHNI_subscription_multiple: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    retail_shares_offered: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    retail_shares_bid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    retail_subscription_multiple: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    employee_subscription: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    shareholder_subscription: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    other_subscription: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    total_subscription: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    retrieval_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("ipo_id", "subscription_date", "subscription_day", "retrieval_timestamp", name="uq_sub_ipo_date_day_time"),
        Index("idx_sub_lookup", "ipo_id", "subscription_date"),
    )


class AnchorHeaderModel(Base):
    """Aggregate anchor placement header (Table: anchors)."""

    __tablename__ = "anchors"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    anchor_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    anchor_allocation: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    anchor_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    anchor_investor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_allocation_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    lock_in_30_day: Mapped[Date] = mapped_column(Date, nullable=False)
    lock_in_90_day: Mapped[Date] = mapped_column(Date, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_anc_ipo", "ipo_id"),
    )


class AnchorInvestorModel(Base):
    """Institutional anchor investor participant roster (Table: anchor_investors)."""

    __tablename__ = "anchor_investors"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    anchor_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("anchors.anchor_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    investor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    investor_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Other")
    allocation_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    allocation_shares: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allocation_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    anchor_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_anc_inv_name", "investor_name"),
        Index("idx_anc_inv_type", "investor_type"),
    )


class GMPLogModel(Base):
    """Indicative Grey Market Premium time-series quotes (Table: gmp)."""

    __tablename__ = "gmp"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    gmp_date: Mapped[Date] = mapped_column(Date, nullable=False)
    gmp_time: Mapped[Time] = mapped_column(Time, nullable=False)
    gmp_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    gmp_percentage: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    reference_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    implied_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Unofficial GMP")
    retrieval_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("ipo_id", "gmp_date", "gmp_time", name="uq_gmp_timeline"),
    )


class PeerCompanyModel(Base):
    """Listed direct peer competitor benchmarks (Table: peers)."""

    __tablename__ = "peers"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    peer_company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    market_cap: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    revenue: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    PAT: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    EPS: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    PE: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    PB: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    ROE: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    ROCE: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    debt_equity: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_peer_lookup", "ipo_id", "ticker"),
    )


class RiskDisclosureModel(Base):
    """Statutory risk factor disclosures (Table: risks)."""

    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    risk_type: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, default="Not available")
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    source_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_risk_lookup", "ipo_id", "risk_type"),
    )


class ScenarioModel(Base):
    """Standardized +40% target scenario hypothesis (Table: scenarios)."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, unique=True
    )
    reference_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    target_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    required_price_movement: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=40.00)
    target_pe: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    target_pb: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    supporting_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Stores JSON string
    contradictory_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Stores JSON string
    scenario_status: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_methodology: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_data_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_scen_status", "ipo_id", "scenario_status"),
    )


class HistoricalPerformanceModel(Base):
    """Post-listing aggregate performance outcomes (Table: historical_performance)."""

    __tablename__ = "historical_performance"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    ipo_year: Mapped[int] = mapped_column(Integer, nullable=False)
    listing_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    listing_day_close: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    listing_day_high: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    listing_day_low: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    listing_day_return: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    post_listing_7d_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    post_listing_30d_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    post_listing_90d_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    post_listing_180d_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    post_listing_1y_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    max_upside_from_issue_price: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    max_drawdown_from_issue_price: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_hist_year_return", "ipo_year", "listing_day_return"),
    )


class PerformanceEventModel(Base):
    """Longitudinal price event stream for post-listing backtesting (Table: performance_events)."""

    __tablename__ = "performance_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ipo_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    event_date: Mapped[Date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    market_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    return_percentage: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    days_from_listing: Mapped[int] = mapped_column(Integer, nullable=False)
    reached_40_percent_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_pevent_lookup", "ipo_id", "event_type", "days_from_listing"),
        Index("idx_pevent_date", "event_date"),
    )


class ScheduledJobExecutionModel(Base):
    """
    Execution state tracking for distributed scheduled jobs (Table: scheduled_job_executions).
    Guarantees exactly-once daily execution and auditability across distributed worker nodes.
    """

    __tablename__ = "scheduled_job_executions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_date: Mapped[Date] = mapped_column(Date, nullable=False)
    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)  # STARTED, COMPLETED, FAILED, SKIPPED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("job_name", "execution_date", name="uq_job_name_execution_date"),
        Index("idx_job_exec_status", "job_name", "execution_status"),
        Index("idx_exec_date", "execution_date"),
    )

