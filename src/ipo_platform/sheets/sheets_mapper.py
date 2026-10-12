"""
Data Mapping Layer for Phase 2 Google Sheets Datastore.
Maps bidirectionally between strongly-typed MasterIPORecord instances and 11 tabular sheet rows.
"""

from typing import Any, Dict, List, Optional
from .sheets_schema import SheetTabName
from ..models.schema import MasterIPORecord
from ..models.enums import (
    SegmentEnum,
    IPOStatusEnum,
    ListingStatusEnum,
    PeriodTypeEnum,
    DataTypeEnum,
    ScenarioStatusEnum,
    ObjectsDisclosureStatusEnum,
)


class SheetsDataMapper:
    """Translates MasterIPORecord datasets into 11 Google Sheets tabular dictionaries."""

    @classmethod
    def record_to_tabular(cls, record: MasterIPORecord) -> Dict[SheetTabName, List[Dict[str, Any]]]:
        """Converts a MasterIPORecord into an 11-tab dictionary of row lists."""
        ipo_id = record.ipo_entity.ipo_id

        # 1. IPO_Master Tab
        master_row = {
            "ipo_id": ipo_id,
            "company_name": record.ipo_entity.company_name,
            "segment": record.ipo_entity.segment.value,
            "status": record.ipo_status.status.value,
            "open_date": record.ipo_status.open_date,
            "close_date": record.ipo_status.close_date,
            "listing_date": record.ipo_status.listing_date,
            "price_band_low": record.issue_structure.price_band_low.value,
            "price_band_high": record.issue_structure.price_band_high.value,
            "issue_price": record.issue_structure.issue_price.value,
            "lot_size": record.issue_structure.lot_size.value,
            "minimum_investment": record.issue_structure.minimum_investment.value,
            "issue_size": record.issue_structure.issue_size.value,
            "fresh_issue_amount": record.issue_structure.fresh_issue_amount.value,
            "ofs_amount": record.issue_structure.ofs_amount.value,
            "fresh_percentage": record.issue_structure.fresh_issue_percentage.value,
            "lead_managers": "Not available",
            "registrar": "Not available",
            "data_cutoff": record.ipo_status.data_cutoff,
        }

        # 2. Financials Tab
        financials_rows = []
        for fin in record.financial_data:
            financials_rows.append(
                {
                    "ipo_id": ipo_id,
                    "period_name": fin.financial_period,
                    "period_type": fin.period_type.value,
                    "revenue": fin.revenue.value if fin.revenue else "Not available",
                    "revenue_growth": fin.revenue_growth.value if fin.revenue_growth else "Not available",
                    "EBITDA": fin.EBITDA.value if fin.EBITDA else "Not available",
                    "EBITDA_margin": fin.EBITDA_margin.value if fin.EBITDA_margin else "Not available",
                    "PAT": fin.PAT.value if fin.PAT else "Not available",
                    "PAT_growth": fin.PAT_growth.value if fin.PAT_growth else "Not available",
                    "EPS": fin.EPS.value if fin.EPS else "Not available",
                    "ROE": fin.ROE.value if fin.ROE else "Not available",
                    "total_debt": fin.total_debt.value if fin.total_debt else "Not available",
                    "debt_equity": fin.debt_equity.value if fin.debt_equity else "Not available",
                    "operating_cash_flow": fin.operating_cash_flow.value if fin.operating_cash_flow else "Not available",
                    "source_ref": "RHP Financial Statements",
                }
            )

        # 3. Subscription Tab
        subscription_rows = []
        if record.subscription_data:
            for cat_name, sub in record.subscription_data.items():
                subscription_rows.append(
                    {
                        "ipo_id": ipo_id,
                        "category": cat_name,
                        "shares_offered": sub.shares_offered,
                        "shares_bid": sub.shares_bid,
                        "subscription_multiple": sub.subscription_multiple,
                        "timestamp": sub.retrieval_timestamp,
                    }
                )

        # 4. Anchors Tab
        anchor_rows = []
        if record.anchor_data and record.anchor_data.anchor_investors:
            for inv in record.anchor_data.anchor_investors:
                anchor_rows.append(
                    {
                        "ipo_id": ipo_id,
                        "investor_name": inv.investor_name,
                        "investor_type": inv.investor_type.value,
                        "amount_cr": inv.allocation_amount,
                        "shares_allotted": inv.allocation_shares,
                        "lock_in_30d": record.anchor_data.lock_in_30_day,
                        "lock_in_90d": record.anchor_data.lock_in_90_day,
                    }
                )

        # 5. GMP Tab
        gmp_rows = []
        if record.gmp_data:
            gmp_rows.append(
                {
                    "ipo_id": ipo_id,
                    "gmp_value": record.gmp_data.gmp_value,
                    "reference_price": record.gmp_data.reference_price,
                    "gmp_percentage": record.gmp_data.gmp_percentage,
                    "quote_timestamp": f"{record.gmp_data.gmp_date} {record.gmp_data.gmp_time}",
                    "source_type": record.gmp_data.source_type.value,
                }
            )

        # 6. Valuation Tab
        valuation_rows = [
            {
                "ipo_id": ipo_id,
                "reference_price": record.valuation_data.reference_price,
                "reference_eps": record.valuation_data.reference_eps,
                "issue_pe": record.valuation_data.issue_pe.value,
                "issue_pb": record.valuation_data.issue_pb.value if record.valuation_data.issue_pb else "Not available",
                "industry_pe": record.valuation_data.industry_pe.value if record.valuation_data.industry_pe else "Not available",
            }
        ]

        # 7. Peers Tab
        peers_rows = []
        for peer in record.peer_companies:
            peers_rows.append(
                {
                    "ipo_id": ipo_id,
                    "peer_name": peer.company_name,
                    "ticker": peer.ticker,
                    "peer_pe": peer.PE if peer.PE is not None else "Not available",
                    "peer_roe": peer.ROE if peer.ROE is not None else "Not available",
                }
            )

        # 8. Risks Tab
        risks_rows = []
        for risk in record.risk_data:
            risks_rows.append(
                {
                    "ipo_id": ipo_id,
                    "risk_category": risk.risk_category.value,
                    "risk_summary": risk.risk_description,
                    "severity": risk.severity.value,
                }
            )

        # 9. Scenarios Tab
        scenarios_rows = [
            {
                "ipo_id": ipo_id,
                "reference_price": record.scenario_40_percent.reference_price,
                "target_price_40": record.scenario_40_percent.target_price,
                "required_move": record.scenario_40_percent.required_price_movement,
                "target_pe": record.scenario_40_percent.target_pe if record.scenario_40_percent.target_pe else "Not available",
                "scenario_status": record.scenario_40_percent.scenario_status.value,
                "evaluation_date": record.scenario_40_percent.scenario_data_timestamp,
            }
        ]

        # 10. Sources Tab
        sources_rows = []
        for src in record.sources:
            sources_rows.append(
                {
                    "source_id": f"SRC-{ipo_id}-01",
                    "ipo_id": ipo_id,
                    "source_name": src.source_name,
                    "source_url": src.source_url or "Not available",
                    "source_type": src.source_type.value,
                }
            )

        # 11. Historical_Performance Tab
        hist_rows = []
        if record.historical_ipo:
            hist_rows.append(
                {
                    "ipo_id": ipo_id,
                    "issue_price": record.issue_structure.price_band_high.value,
                    "listing_open": record.historical_ipo.listing_price,
                    "listing_close": record.historical_ipo.listing_day_close,
                    "listing_return": record.historical_ipo.listing_day_return,
                    "post_30d_return": record.historical_ipo.post_listing_30d_return,
                    "reached_40_target": "Not available",
                }
            )

        return {
            SheetTabName.IPO_MASTER: [master_row],
            SheetTabName.FINANCIALS: financials_rows,
            SheetTabName.SUBSCRIPTION: subscription_rows,
            SheetTabName.ANCHORS: anchor_rows,
            SheetTabName.GMP: gmp_rows,
            SheetTabName.VALUATION: valuation_rows,
            SheetTabName.PEERS: peers_rows,
            SheetTabName.RISKS: risks_rows,
            SheetTabName.SCENARIOS: scenarios_rows,
            SheetTabName.SOURCES: sources_rows,
            SheetTabName.HISTORICAL_PERFORMANCE: hist_rows,
        }
