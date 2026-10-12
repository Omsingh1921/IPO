"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-01 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Sources Table
    op.create_table(
        "sources",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(64), nullable=False, unique=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(), nullable=False),
        sa.Column("page_or_section", sa.String(255), nullable=True),
        sa.Column("data_type", sa.String(64), nullable=False, server_default="Reported"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_source_type_date", "sources", ["source_type", "publication_date"])

    # 2. IPO Master Table (Includes version_id OCC)
    op.create_table(
        "ipo_master",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), nullable=False, unique=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("company_legal_name", sa.String(255), nullable=False),
        sa.Column("ticker_symbol", sa.String(32), nullable=True),
        sa.Column("isin", sa.String(12), nullable=True, unique=True),
        sa.Column("segment", sa.String(64), nullable=False),
        sa.Column("sector", sa.String(128), nullable=False),
        sa.Column("industry", sa.String(128), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("research_date", sa.Date(), nullable=False),
        sa.Column("research_time", sa.Time(), nullable=False),
        sa.Column("data_cutoff", sa.DateTime(), nullable=False),
        sa.Column("open_date", sa.Date(), nullable=False),
        sa.Column("close_date", sa.Date(), nullable=False),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("listing_status", sa.String(64), nullable=False, server_default="Pre-Listing"),
        sa.Column("issue_size", sa.Numeric(14, 2), nullable=False),
        sa.Column("fresh_issue_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("ofs_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("fresh_issue_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("ofs_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("face_value", sa.Numeric(8, 2), nullable=False),
        sa.Column("price_band_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_band_high", sa.Numeric(10, 2), nullable=False),
        sa.Column("issue_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("lot_size", sa.Integer(), nullable=False),
        sa.Column("minimum_investment", sa.Numeric(12, 2), nullable=False),
        sa.Column("employee_reservation", sa.Numeric(12, 2), nullable=True),
        sa.Column("shareholder_reservation", sa.Numeric(12, 2), nullable=True),
        sa.Column("other_reservation", sa.Numeric(12, 2), nullable=True),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ipo_status_dates", "ipo_master", ["status", "open_date", "close_date"])
    op.create_index("idx_ipo_segment_sector", "ipo_master", ["segment", "sector"])
    op.create_index("idx_ipo_listing_date", "ipo_master", ["listing_date"])

    # 3. Objects of Issue Table
    op.create_table(
        "ipo_objects_of_issue",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("purpose_type", sa.String(64), nullable=False),
        sa.Column("purpose_description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("percentage_of_fresh_issue", sa.Numeric(5, 2), nullable=True),
        sa.Column("disclosure_status", sa.String(64), nullable=False, server_default="Disclosed"),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_obj_ipo_purpose", "ipo_objects_of_issue", ["ipo_id", "purpose_type"])

    # 4. Financials Table
    op.create_table(
        "financials",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("financial_period", sa.String(32), nullable=False),
        sa.Column("period_type", sa.String(64), nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("revenue_growth", sa.Numeric(8, 2), nullable=True),
        sa.Column("EBITDA", sa.Numeric(14, 2), nullable=True),
        sa.Column("EBITDA_margin", sa.Numeric(6, 2), nullable=True),
        sa.Column("PAT", sa.Numeric(14, 2), nullable=True),
        sa.Column("PAT_growth", sa.Numeric(8, 2), nullable=True),
        sa.Column("EPS", sa.Numeric(10, 2), nullable=True),
        sa.Column("book_value_per_share", sa.Numeric(10, 2), nullable=True),
        sa.Column("ROE", sa.Numeric(6, 2), nullable=True),
        sa.Column("ROCE", sa.Numeric(6, 2), nullable=True),
        sa.Column("total_debt", sa.Numeric(14, 2), nullable=True),
        sa.Column("net_debt", sa.Numeric(14, 2), nullable=True),
        sa.Column("debt_equity", sa.Numeric(6, 2), nullable=True),
        sa.Column("operating_cash_flow", sa.Numeric(14, 2), nullable=True),
        sa.Column("investing_cash_flow", sa.Numeric(14, 2), nullable=True),
        sa.Column("financing_cash_flow", sa.Numeric(14, 2), nullable=True),
        sa.Column("free_cash_flow", sa.Numeric(14, 2), nullable=True),
        sa.Column("data_type", sa.String(64), nullable=False, server_default="Reported"),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ipo_id", "financial_period", name="uq_fin_ipo_period"),
    )
    op.create_index("idx_fin_period_type", "financials", ["ipo_id", "period_type", "financial_period"])

    # 5. Valuation Table
    op.create_table(
        "valuation",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("issue_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("reference_eps", sa.Numeric(10, 2), nullable=True),
        sa.Column("reference_book_value_per_share", sa.Numeric(10, 2), nullable=True),
        sa.Column("issue_pe", sa.Numeric(8, 2), nullable=True),
        sa.Column("issue_pb", sa.Numeric(8, 2), nullable=True),
        sa.Column("industry_pe", sa.Numeric(8, 2), nullable=True),
        sa.Column("industry_pb", sa.Numeric(8, 2), nullable=True),
        sa.Column("peer_average_pe", sa.Numeric(8, 2), nullable=True),
        sa.Column("peer_average_pb", sa.Numeric(8, 2), nullable=True),
        sa.Column("valuation_method", sa.String(255), nullable=True),
        sa.Column("valuation_source", sa.String(255), nullable=True),
        sa.Column("valuation_date", sa.Date(), nullable=True),
        sa.Column("data_type", sa.String(64), nullable=False, server_default="Calculated"),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_val_ipo", "valuation", ["ipo_id"])

    # 6. Subscription Table
    op.create_table(
        "subscription",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("subscription_date", sa.Date(), nullable=False),
        sa.Column("subscription_day", sa.String(16), nullable=False),
        sa.Column("QIB_shares_offered", sa.BigInteger(), nullable=True),
        sa.Column("QIB_shares_bid", sa.BigInteger(), nullable=True),
        sa.Column("QIB_subscription_multiple", sa.Numeric(8, 2), nullable=True),
        sa.Column("NII_total_shares_offered", sa.BigInteger(), nullable=True),
        sa.Column("NII_total_shares_bid", sa.BigInteger(), nullable=True),
        sa.Column("NII_total_subscription_multiple", sa.Numeric(8, 2), nullable=True),
        sa.Column("sHNI_shares_offered", sa.BigInteger(), nullable=True),
        sa.Column("sHNI_shares_bid", sa.BigInteger(), nullable=True),
        sa.Column("sHNI_subscription_multiple", sa.Numeric(8, 2), nullable=True),
        sa.Column("bHNI_shares_offered", sa.BigInteger(), nullable=True),
        sa.Column("bHNI_shares_bid", sa.BigInteger(), nullable=True),
        sa.Column("bHNI_subscription_multiple", sa.Numeric(8, 2), nullable=True),
        sa.Column("retail_shares_offered", sa.BigInteger(), nullable=True),
        sa.Column("retail_shares_bid", sa.BigInteger(), nullable=True),
        sa.Column("retail_subscription_multiple", sa.Numeric(8, 2), nullable=True),
        sa.Column("employee_subscription", sa.Numeric(8, 2), nullable=True),
        sa.Column("shareholder_subscription", sa.Numeric(8, 2), nullable=True),
        sa.Column("other_subscription", sa.Numeric(8, 2), nullable=True),
        sa.Column("total_subscription", sa.Numeric(8, 2), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ipo_id", "subscription_date", "subscription_day", "retrieval_timestamp", name="uq_sub_ipo_date_day_time"),
    )
    op.create_index("idx_sub_lookup", "subscription", ["ipo_id", "subscription_date"])

    # 7. Anchors Table
    op.create_table(
        "anchors",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("anchor_id", sa.String(64), nullable=False, unique=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("anchor_allocation", sa.Numeric(12, 2), nullable=False),
        sa.Column("anchor_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("anchor_investor_count", sa.Integer(), nullable=False),
        sa.Column("anchor_allocation_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("lock_in_30_day", sa.Date(), nullable=False),
        sa.Column("lock_in_90_day", sa.Date(), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_anc_ipo", "anchors", ["ipo_id"])

    # 8. Anchor Investors Table
    op.create_table(
        "anchor_investors",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("anchor_id", sa.String(64), sa.ForeignKey("anchors.anchor_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("investor_name", sa.String(255), nullable=False),
        sa.Column("investor_type", sa.String(64), nullable=False, server_default="Other"),
        sa.Column("allocation_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("allocation_shares", sa.BigInteger(), nullable=False),
        sa.Column("allocation_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("anchor_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_anc_inv_name", "anchor_investors", ["investor_name"])
    op.create_index("idx_anc_inv_type", "anchor_investors", ["investor_type"])

    # 9. GMP Table
    op.create_table(
        "gmp",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("gmp_date", sa.Date(), nullable=False),
        sa.Column("gmp_time", sa.Time(), nullable=False),
        sa.Column("gmp_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("gmp_percentage", sa.Numeric(6, 2), nullable=True),
        sa.Column("reference_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("implied_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False, server_default="Unofficial GMP"),
        sa.Column("retrieval_timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ipo_id", "gmp_date", "gmp_time", name="uq_gmp_timeline"),
    )

    # 10. Peers Table
    op.create_table(
        "peers",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("peer_company_name", sa.String(255), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("market_cap", sa.Numeric(14, 2), nullable=True),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("PAT", sa.Numeric(14, 2), nullable=True),
        sa.Column("EPS", sa.Numeric(10, 2), nullable=True),
        sa.Column("PE", sa.Numeric(8, 2), nullable=True),
        sa.Column("PB", sa.Numeric(8, 2), nullable=True),
        sa.Column("ROE", sa.Numeric(6, 2), nullable=True),
        sa.Column("ROCE", sa.Numeric(6, 2), nullable=True),
        sa.Column("debt_equity", sa.Numeric(6, 2), nullable=True),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_peer_lookup", "peers", ["ipo_id", "ticker"])

    # 11. Risks Table
    op.create_table(
        "risks",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("risk_type", sa.String(64), nullable=False),
        sa.Column("risk_description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(64), nullable=False, server_default="Not available"),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_risk_lookup", "risks", ["ipo_id", "risk_type"])

    # 12. Scenarios Table
    op.create_table(
        "scenarios",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("reference_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("target_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("required_price_movement", sa.Numeric(5, 2), nullable=False, server_default="40.00"),
        sa.Column("target_pe", sa.Numeric(8, 2), nullable=True),
        sa.Column("target_pb", sa.Numeric(8, 2), nullable=True),
        sa.Column("supporting_factors", sa.Text(), nullable=True),
        sa.Column("contradictory_factors", sa.Text(), nullable=True),
        sa.Column("scenario_status", sa.String(64), nullable=False),
        sa.Column("scenario_methodology", sa.Text(), nullable=False),
        sa.Column("scenario_data_timestamp", sa.DateTime(), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_scen_status", "scenarios", ["ipo_id", "scenario_status"])

    # 13. Historical Performance Table
    op.create_table(
        "historical_performance",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("ipo_year", sa.Integer(), nullable=False),
        sa.Column("listing_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("listing_day_close", sa.Numeric(10, 2), nullable=False),
        sa.Column("listing_day_high", sa.Numeric(10, 2), nullable=True),
        sa.Column("listing_day_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("listing_day_return", sa.Numeric(8, 2), nullable=False),
        sa.Column("post_listing_7d_return", sa.Numeric(8, 2), nullable=True),
        sa.Column("post_listing_30d_return", sa.Numeric(8, 2), nullable=True),
        sa.Column("post_listing_90d_return", sa.Numeric(8, 2), nullable=True),
        sa.Column("post_listing_180d_return", sa.Numeric(8, 2), nullable=True),
        sa.Column("post_listing_1y_return", sa.Numeric(8, 2), nullable=True),
        sa.Column("max_upside_from_issue_price", sa.Numeric(8, 2), nullable=True),
        sa.Column("max_drawdown_from_issue_price", sa.Numeric(8, 2), nullable=True),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_hist_year_return", "historical_performance", ["ipo_year", "listing_day_return"])

    # 14. Performance Events Table
    op.create_table(
        "performance_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ipo_id", sa.String(64), sa.ForeignKey("ipo_master.ipo_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("reference_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("market_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("return_percentage", sa.Numeric(8, 2), nullable=False),
        sa.Column("days_from_listing", sa.Integer(), nullable=False),
        sa.Column("reached_40_percent_target", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_pevent_lookup", "performance_events", ["ipo_id", "event_type", "days_from_listing"])
    op.create_index("idx_pevent_date", "performance_events", ["event_date"])


def downgrade() -> None:
    op.drop_table("performance_events")
    op.drop_table("historical_performance")
    op.drop_table("scenarios")
    op.drop_table("risks")
    op.drop_table("peers")
    op.drop_table("gmp")
    op.drop_table("anchor_investors")
    op.drop_table("anchors")
    op.drop_table("subscription")
    op.drop_table("valuation")
    op.drop_table("financials")
    op.drop_table("ipo_objects_of_issue")
    op.drop_table("ipo_master")
    op.drop_table("sources")
