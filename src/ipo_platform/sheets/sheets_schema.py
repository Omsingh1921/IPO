"""
Tabular Schema definitions for 11-Tab Google Sheets Datastore (Phase 2).
Enforces exact column headers, required fields, and data types per docs/ipo-data-schema.md Section 4.
"""

from enum import Enum
from typing import Dict, List


class SheetTabName(str, Enum):
    IPO_MASTER = "IPO_Master"
    FINANCIALS = "Financials"
    SUBSCRIPTION = "Subscription"
    ANCHORS = "Anchors"
    GMP = "GMP"
    VALUATION = "Valuation"
    PEERS = "Peers"
    RISKS = "Risks"
    SCENARIOS = "Scenarios"
    SOURCES = "Sources"
    HISTORICAL_PERFORMANCE = "Historical_Performance"


# Exact column header contracts per docs/ipo-data-schema.md Section 4
GOOGLE_SHEETS_TAB_HEADERS: Dict[SheetTabName, List[str]] = {
    SheetTabName.IPO_MASTER: [
        "ipo_id",
        "company_name",
        "segment",
        "status",
        "open_date",
        "close_date",
        "listing_date",
        "price_band_low",
        "price_band_high",
        "issue_price",
        "lot_size",
        "minimum_investment",
        "issue_size",
        "fresh_issue_amount",
        "ofs_amount",
        "fresh_percentage",
        "lead_managers",
        "registrar",
        "data_cutoff",
    ],
    SheetTabName.FINANCIALS: [
        "ipo_id",
        "period_name",
        "period_type",
        "revenue",
        "revenue_growth",
        "EBITDA",
        "EBITDA_margin",
        "PAT",
        "PAT_growth",
        "EPS",
        "ROE",
        "total_debt",
        "debt_equity",
        "operating_cash_flow",
        "source_ref",
    ],
    SheetTabName.SUBSCRIPTION: [
        "ipo_id",
        "category",
        "shares_offered",
        "shares_bid",
        "subscription_multiple",
        "timestamp",
    ],
    SheetTabName.ANCHORS: [
        "ipo_id",
        "investor_name",
        "investor_type",
        "amount_cr",
        "shares_allotted",
        "lock_in_30d",
        "lock_in_90d",
    ],
    SheetTabName.GMP: [
        "ipo_id",
        "gmp_value",
        "reference_price",
        "gmp_percentage",
        "quote_timestamp",
        "source_type",
    ],
    SheetTabName.VALUATION: [
        "ipo_id",
        "reference_price",
        "reference_eps",
        "issue_pe",
        "issue_pb",
        "industry_pe",
    ],
    SheetTabName.PEERS: [
        "ipo_id",
        "peer_name",
        "ticker",
        "peer_pe",
        "peer_roe",
    ],
    SheetTabName.RISKS: [
        "ipo_id",
        "risk_category",
        "risk_summary",
        "severity",
    ],
    SheetTabName.SCENARIOS: [
        "ipo_id",
        "reference_price",
        "target_price_40",
        "required_move",
        "target_pe",
        "scenario_status",
        "evaluation_date",
    ],
    SheetTabName.SOURCES: [
        "source_id",
        "ipo_id",
        "source_name",
        "source_url",
        "source_type",
    ],
    SheetTabName.HISTORICAL_PERFORMANCE: [
        "ipo_id",
        "issue_price",
        "listing_open",
        "listing_close",
        "listing_return",
        "post_30d_return",
        "reached_40_target",
    ],
}
