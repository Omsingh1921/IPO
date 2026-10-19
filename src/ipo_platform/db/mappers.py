"""
Bidirectional Data Mapping Layer for Indian IPO Platform.
Translates seamlessly between domain MasterIPORecord aggregate dataclasses
and SQLAlchemy 2.0 ORM physical models while preserving metadata and provenance.
"""

import json
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Union

from ipo_platform.db.models import (
    AnchorHeaderModel,
    AnchorInvestorModel,
    FinancialModel,
    GMPLogModel,
    HistoricalPerformanceModel,
    IPOMasterModel,
    ObjectOfIssueModel,
    PeerCompanyModel,
    PerformanceEventModel,
    RiskDisclosureModel,
    ScenarioModel,
    SourceModel,
    SubscriptionModel,
    ValuationModel,
)
from ipo_platform.models.enums import (
    DataCompletenessEnum,
    DataTypeEnum,
    InvestorTypeEnum,
    IPOStatusEnum,
    ListingStatusEnum,
    ObjectsDisclosureStatusEnum,
    PerformanceEventTypeEnum,
    PeriodTypeEnum,
    RiskCategoryEnum,
    RiskSeverityEnum,
    ScenarioStatusEnum,
    SegmentEnum,
    SourceTypeEnum,
    SourceVerificationEnum,
)
from ipo_platform.models.schema import (
    AnchorData,
    AnchorInvestor,
    DataQuality,
    FinancialRecord,
    GMPData,
    HistoricalIPO,
    IPOEntity,
    IPOStatus,
    IssueStructure,
    MasterIPORecord,
    ObjectOfIssue,
    PeerCompany,
    PerformanceEvent,
    ProvenanceEnvelope,
    RiskRecord,
    Scenario40Percent,
    SourceRecord,
    SubscriptionCategory,
    ValuationData,
)

# -----------------------------------------------------------------------------
# Type Safety & Date Helper Functions
# -----------------------------------------------------------------------------


def to_float_safe(val: Any) -> Optional[float]:
    """Safely converts value or ProvenanceEnvelope value to float, or returns None."""
    if val is None or val == "Not available":
        return None
    if isinstance(val, ProvenanceEnvelope):
        return to_float_safe(val.value)
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def to_int_safe(val: Any) -> Optional[int]:
    """Safely converts value or ProvenanceEnvelope value to int, or returns None."""
    if val is None or val == "Not available":
        return None
    if isinstance(val, ProvenanceEnvelope):
        return to_int_safe(val.value)
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def parse_date_safe(val: Any) -> Optional[date]:
    """Safely parses string ISO format date into datetime.date object."""
    if isinstance(val, date):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return date.fromisoformat(val.strip()[:10])
        except ValueError:
            return None
    return None


def format_date_safe(val: Any) -> Optional[str]:
    """Formats datetime.date to ISO string."""
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, str):
        return val
    return None


def parse_time_safe(val: Any) -> Optional[time]:
    """Safely parses string time (HH:MM:SS) into datetime.time object."""
    if isinstance(val, time):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return time.fromisoformat(val.strip())
        except ValueError:
            return None
    return None


def format_time_safe(val: Any) -> Optional[str]:
    """Formats datetime.time to ISO string."""
    if isinstance(val, time):
        return val.isoformat()
    if isinstance(val, str):
        return val
    return None


def parse_datetime_safe(val: Any) -> Optional[datetime]:
    """Safely parses string ISO format datetime into datetime.datetime object."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        clean_str = val.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_str)
        except ValueError:
            return None
    return None


def format_datetime_safe(val: Any) -> Optional[str]:
    """Formats datetime.datetime to ISO string."""
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, str):
        return val
    return None


def build_provenance_envelope(
    val: Any,
    unit: Optional[str] = None,
    currency: Optional[str] = "INR",
    data_type: DataTypeEnum = DataTypeEnum.REPORTED,
    source: str = "RHP",
    source_date: Optional[str] = None,
    retrieval_timestamp: Optional[str] = None,
) -> ProvenanceEnvelope:
    """Helper to reconstruct ProvenanceEnvelope for domain dataclasses."""
    if isinstance(val, ProvenanceEnvelope):
        return val
    value = val if val is not None else "Not available"
    return ProvenanceEnvelope(
        value=value,
        unit=unit,
        currency=currency,
        data_type=data_type,
        source=source,
        source_date=source_date,
        retrieval_timestamp=retrieval_timestamp,
    )


# -----------------------------------------------------------------------------
# Core Bidirectional Mapper Class
# -----------------------------------------------------------------------------


class MasterIPOMapper:
    """Translates bidirectionally between domain MasterIPORecord and SQLAlchemy 2.0 ORM models."""

    @classmethod
    def record_to_models(cls, record: MasterIPORecord) -> Dict[str, Any]:
        """
        Maps a MasterIPORecord domain aggregate into a dictionary of physical ORM models.

        Returns:
            Dict containing:
                "master": IPOMasterModel
                "sources": List[SourceModel]
                "objects_of_issue": List[ObjectOfIssueModel]
                "financials": List[FinancialModel]
                "valuation": Optional[ValuationModel]
                "subscriptions": List[SubscriptionModel]
                "anchor_header": Optional[AnchorHeaderModel]
                "anchor_investors": List[AnchorInvestorModel]
                "gmp_logs": List[GMPLogModel]
                "peers": List[PeerCompanyModel]
                "risks": List[RiskDisclosureModel]
                "scenario": Optional[ScenarioModel]
                "historical_performance": Optional[HistoricalPerformanceModel]
                "performance_events": List[PerformanceEventModel]
        """
        ipo_id = record.ipo_entity.ipo_id

        # 1. Sources Mapping
        sources_models: List[SourceModel] = []
        for idx, src in enumerate(record.sources):
            source_id = f"SRC_{ipo_id}_{idx + 1}"
            sources_models.append(
                SourceModel(
                    source_id=source_id,
                    source_name=src.source_name,
                    source_url=src.source_url,
                    source_type=src.source_type.value if isinstance(src.source_type, SourceTypeEnum) else str(src.source_type),
                    publication_date=parse_date_safe(src.publication_date),
                    retrieval_timestamp=parse_datetime_safe(src.retrieval_timestamp) or datetime.now(),
                    page_or_section=src.page_or_section,
                    data_type=src.data_type.value if isinstance(src.data_type, DataTypeEnum) else str(src.data_type),
                    notes=src.notes,
                )
            )

        primary_source_id = sources_models[0].source_id if sources_models else None

        # 2. Master IPO Model
        iss = record.issue_structure
        master_model = IPOMasterModel(
            ipo_id=ipo_id,
            company_name=record.ipo_entity.company_name,
            company_legal_name=record.ipo_entity.company_legal_name,
            ticker_symbol=record.ipo_entity.ticker_symbol,
            isin=record.ipo_entity.isin,
            segment=record.ipo_entity.segment.value if isinstance(record.ipo_entity.segment, SegmentEnum) else str(record.ipo_entity.segment),
            sector=record.ipo_entity.sector,
            industry=record.ipo_entity.industry,
            status=record.ipo_status.status.value if isinstance(record.ipo_status.status, IPOStatusEnum) else str(record.ipo_status.status),
            research_date=parse_date_safe(record.ipo_status.research_date) or date.today(),
            research_time=parse_time_safe(record.ipo_status.research_time) or time(10, 0),
            data_cutoff=parse_datetime_safe(record.ipo_status.data_cutoff) or datetime.now(),
            open_date=parse_date_safe(record.ipo_status.open_date) or date.today(),
            close_date=parse_date_safe(record.ipo_status.close_date) or date.today(),
            allotment_date=parse_date_safe(getattr(record.ipo_status, "allotment_date", None)),
            listing_date=parse_date_safe(record.ipo_status.listing_date),
            listing_status=record.ipo_status.listing_status.value if isinstance(record.ipo_status.listing_status, ListingStatusEnum) else str(record.ipo_status.listing_status),
            issue_size=(
                round(((to_float_safe(iss.issue_size) or 0.0) * (to_float_safe(iss.price_band_high) or to_float_safe(iss.issue_price) or 100.0)) / 10000000.0, 2)
                if (to_float_safe(iss.issue_size) or 0.0) > 50000
                else (to_float_safe(iss.issue_size) or 0.0)
            ),
            fresh_issue_amount=(
                round(((to_float_safe(iss.fresh_issue_amount) or 0.0) * (to_float_safe(iss.price_band_high) or to_float_safe(iss.issue_price) or 100.0)) / 10000000.0, 2)
                if (to_float_safe(iss.fresh_issue_amount) or 0.0) > 50000
                else (to_float_safe(iss.fresh_issue_amount) or 0.0)
            ),
            ofs_amount=(
                round(((to_float_safe(iss.ofs_amount) or 0.0) * (to_float_safe(iss.price_band_high) or to_float_safe(iss.issue_price) or 100.0)) / 10000000.0, 2)
                if (to_float_safe(iss.ofs_amount) or 0.0) > 50000
                else (to_float_safe(iss.ofs_amount) or 0.0)
            ),
            fresh_issue_percentage=to_float_safe(iss.fresh_issue_percentage),
            ofs_percentage=to_float_safe(iss.ofs_percentage),
            face_value=to_float_safe(iss.face_value) or 10.0,
            price_band_low=to_float_safe(iss.price_band_low),
            price_band_high=to_float_safe(iss.price_band_high) or 0.0,
            issue_price=to_float_safe(iss.issue_price),
            lot_size=to_int_safe(iss.lot_size) or 1,
            minimum_investment=to_float_safe(iss.minimum_investment) or 0.0,
            employee_reservation=to_float_safe(iss.employee_reservation),
            shareholder_reservation=to_float_safe(iss.shareholder_reservation),
            other_reservation=to_float_safe(iss.other_reservation),
            source_id=primary_source_id,
            version_id=1,
        )

        # 3. Objects of Issue Mapping
        objects_models: List[ObjectOfIssueModel] = []
        for obj in record.objects_of_issue:
            objects_models.append(
                ObjectOfIssueModel(
                    ipo_id=ipo_id,
                    purpose_type=obj.purpose[:64] if obj.purpose else "General",
                    purpose_description=obj.purpose,
                    amount=obj.amount,
                    percentage_of_fresh_issue=obj.percentage_of_fresh_issue,
                    disclosure_status=obj.disclosure_status.value if isinstance(obj.disclosure_status, ObjectsDisclosureStatusEnum) else str(obj.disclosure_status),
                    source_id=primary_source_id,
                )
            )

        # 4. Financial Records Mapping
        financial_models: List[FinancialModel] = []
        for fin in record.financial_data:
            financial_models.append(
                FinancialModel(
                    ipo_id=ipo_id,
                    financial_period=fin.financial_period,
                    period_type=fin.period_type.value if isinstance(fin.period_type, PeriodTypeEnum) else str(fin.period_type),
                    revenue=to_float_safe(fin.revenue),
                    revenue_growth=to_float_safe(fin.revenue_growth),
                    EBITDA=to_float_safe(fin.EBITDA),
                    EBITDA_margin=to_float_safe(fin.EBITDA_margin),
                    PAT=to_float_safe(fin.PAT),
                    PAT_growth=to_float_safe(fin.PAT_growth),
                    EPS=to_float_safe(fin.EPS),
                    book_value_per_share=to_float_safe(fin.book_value_per_share),
                    ROE=to_float_safe(fin.ROE),
                    ROCE=to_float_safe(fin.ROCE),
                    total_debt=to_float_safe(fin.total_debt),
                    net_debt=to_float_safe(fin.net_debt),
                    debt_equity=to_float_safe(fin.debt_equity),
                    operating_cash_flow=to_float_safe(fin.operating_cash_flow),
                    investing_cash_flow=to_float_safe(fin.investing_cash_flow),
                    financing_cash_flow=to_float_safe(fin.financing_cash_flow),
                    free_cash_flow=to_float_safe(fin.free_cash_flow),
                    data_type=fin.revenue.data_type.value if fin.revenue and isinstance(fin.revenue.data_type, DataTypeEnum) else "Reported",
                    source_id=primary_source_id,
                )
            )

        # 5. Valuation Data Mapping
        val = record.valuation_data
        valuation_model = ValuationModel(
            ipo_id=ipo_id,
            issue_price=val.reference_price,
            reference_eps=val.reference_eps,
            reference_book_value_per_share=val.reference_book_value_per_share,
            issue_pe=to_float_safe(val.issue_pe),
            issue_pb=to_float_safe(val.issue_pb),
            industry_pe=to_float_safe(val.industry_pe),
            industry_pb=to_float_safe(val.industry_pb),
            peer_average_pe=to_float_safe(val.peer_average_pe),
            peer_average_pb=to_float_safe(val.peer_average_pb),
            valuation_method=val.valuation_method,
            valuation_source=val.valuation_source,
            valuation_date=parse_date_safe(val.valuation_date),
            source_id=primary_source_id,
        )

        # 6. Subscription Mapping
        sub_dict = record.subscription_data
        subscription_models: List[SubscriptionModel] = []
        if sub_dict:
            qib = sub_dict.get("QIB") or sub_dict.get("qib")
            nii = sub_dict.get("NII") or sub_dict.get("nii")
            shni = sub_dict.get("sHNI") or sub_dict.get("shni")
            bhni = sub_dict.get("bHNI") or sub_dict.get("bhni")
            retail = sub_dict.get("Retail") or sub_dict.get("retail")
            emp = sub_dict.get("Employee") or sub_dict.get("employee")
            sh = sub_dict.get("Shareholder") or sub_dict.get("shareholder")
            oth = sub_dict.get("Other") or sub_dict.get("other")

            ref_sub = qib or retail or nii or next(iter(sub_dict.values()))
            sub_date = parse_date_safe(ref_sub.source_date) or date.today()
            sub_time = parse_datetime_safe(ref_sub.retrieval_timestamp) or datetime.now()

            # Calculate overall subscription
            if "Total" in sub_dict and sub_dict["Total"].subscription_multiple is not None:
                tot_mult = float(sub_dict["Total"].subscription_multiple)
            elif "Overall" in sub_dict and sub_dict["Overall"].subscription_multiple is not None:
                tot_mult = float(sub_dict["Overall"].subscription_multiple)
            else:
                tot_mult = max([s.subscription_multiple for s in sub_dict.values() if s.subscription_multiple is not None] or [0.0])

            subscription_models.append(
                SubscriptionModel(
                    ipo_id=ipo_id,
                    subscription_date=sub_date,
                    subscription_day="Final",
                    QIB_shares_offered=qib.shares_offered if qib else None,
                    QIB_shares_bid=qib.shares_bid if qib else None,
                    QIB_subscription_multiple=qib.subscription_multiple if qib else None,
                    NII_total_shares_offered=nii.shares_offered if nii else None,
                    NII_total_shares_bid=nii.shares_bid if nii else None,
                    NII_total_subscription_multiple=nii.subscription_multiple if nii else None,
                    sHNI_shares_offered=shni.shares_offered if shni else None,
                    sHNI_shares_bid=shni.shares_bid if shni else None,
                    sHNI_subscription_multiple=shni.subscription_multiple if shni else None,
                    bHNI_shares_offered=bhni.shares_offered if bhni else None,
                    bHNI_shares_bid=bhni.shares_bid if bhni else None,
                    bHNI_subscription_multiple=bhni.subscription_multiple if bhni else None,
                    retail_shares_offered=retail.shares_offered if retail else None,
                    retail_shares_bid=retail.shares_bid if retail else None,
                    retail_subscription_multiple=retail.subscription_multiple if retail else None,
                    employee_subscription=emp.subscription_multiple if emp else None,
                    shareholder_subscription=sh.subscription_multiple if sh else None,
                    other_subscription=oth.subscription_multiple if oth else None,
                    total_subscription=tot_mult,
                    retrieval_timestamp=sub_time,
                    source_id=primary_source_id,
                )
            )

        # 7. Anchor Placement Mapping
        anchor_header_model: Optional[AnchorHeaderModel] = None
        anchor_investor_models: List[AnchorInvestorModel] = []
        if record.anchor_data:
            anc = record.anchor_data
            anchor_id = f"ANC_{ipo_id}"
            anchor_header_model = AnchorHeaderModel(
                anchor_id=anchor_id,
                ipo_id=ipo_id,
                anchor_allocation=anc.anchor_allocation,
                anchor_price=anc.anchor_price,
                anchor_investor_count=anc.anchor_investor_count,
                anchor_allocation_percentage=anc.anchor_allocation_percentage,
                lock_in_30_day=parse_date_safe(anc.lock_in_30_day) or date.today(),
                lock_in_90_day=parse_date_safe(anc.lock_in_90_day) or date.today(),
                source_id=primary_source_id,
            )

            for inv in anc.anchor_investors:
                anchor_investor_models.append(
                    AnchorInvestorModel(
                        anchor_id=anchor_id,
                        investor_name=inv.investor_name,
                        investor_type=inv.investor_type.value if isinstance(inv.investor_type, InvestorTypeEnum) else str(inv.investor_type),
                        allocation_amount=inv.allocation_amount,
                        allocation_shares=inv.allocation_shares,
                        allocation_percentage=inv.allocation_percentage,
                        anchor_price=anc.anchor_price,
                        source_id=primary_source_id,
                    )
                )

        # 8. GMP Logs Mapping
        gmp_models: List[GMPLogModel] = []
        if record.gmp_data:
            gmp = record.gmp_data
            gmp_models.append(
                GMPLogModel(
                    ipo_id=ipo_id,
                    gmp_date=parse_date_safe(gmp.gmp_date) or date.today(),
                    gmp_time=parse_time_safe(gmp.gmp_time) or time(10, 0),
                    gmp_value=gmp.gmp_value,
                    gmp_percentage=gmp.gmp_percentage,
                    reference_price=gmp.reference_price,
                    implied_price=gmp.implied_price,
                    source_type=gmp.source_type.value if isinstance(gmp.source_type, SourceTypeEnum) else str(gmp.source_type),
                    retrieval_timestamp=datetime.now(),
                    source_id=primary_source_id,
                )
            )

        # 9. Peer Companies Mapping
        peer_models: List[PeerCompanyModel] = []
        for peer in record.peer_companies:
            peer_models.append(
                PeerCompanyModel(
                    ipo_id=ipo_id,
                    peer_company_name=peer.company_name,
                    ticker=peer.ticker,
                    market_cap=peer.market_cap,
                    revenue=peer.revenue,
                    PAT=peer.PAT,
                    EPS=peer.EPS,
                    PE=peer.PE,
                    PB=peer.PB,
                    ROE=peer.ROE,
                    ROCE=peer.ROCE,
                    debt_equity=peer.debt_equity,
                    source_id=primary_source_id,
                )
            )

        # 10. Risk Disclosures Mapping
        risk_models: List[RiskDisclosureModel] = []
        for risk in record.risk_data:
            risk_models.append(
                RiskDisclosureModel(
                    ipo_id=ipo_id,
                    risk_type=risk.risk_category.value if isinstance(risk.risk_category, RiskCategoryEnum) else str(risk.risk_category),
                    risk_description=risk.risk_description,
                    severity=risk.severity.value if isinstance(risk.severity, RiskSeverityEnum) else str(risk.severity),
                    source_id=primary_source_id,
                )
            )

        # 11. Scenario Mapping
        scen = record.scenario_40_percent
        scenario_model = ScenarioModel(
            ipo_id=ipo_id,
            reference_price=scen.reference_price,
            target_price=scen.target_price,
            required_price_movement=scen.required_price_movement,
            target_pe=scen.target_pe,
            target_pb=scen.target_pb,
            supporting_factors=json.dumps(scen.supporting_factors),
            contradictory_factors=json.dumps(scen.contradictory_factors),
            scenario_status=scen.scenario_status.value if isinstance(scen.scenario_status, ScenarioStatusEnum) else str(scen.scenario_status),
            scenario_methodology=scen.scenario_methodology,
            scenario_data_timestamp=parse_datetime_safe(scen.scenario_data_timestamp) or datetime.now(),
            source_id=primary_source_id,
        )

        # 12. Historical Performance Mapping
        hist_model: Optional[HistoricalPerformanceModel] = None
        if record.historical_ipo:
            h = record.historical_ipo
            hist_model = HistoricalPerformanceModel(
                ipo_id=ipo_id,
                ipo_year=h.ipo_year or date.today().year,
                listing_price=to_float_safe(h.listing_price) or 0.0,
                listing_day_close=to_float_safe(h.listing_day_close) or 0.0,
                listing_day_high=to_float_safe(h.listing_day_high),
                listing_day_low=to_float_safe(h.listing_day_low),
                listing_day_return=to_float_safe(h.listing_day_return) or 0.0,
                post_listing_7d_return=to_float_safe(h.post_listing_7d_return),
                post_listing_30d_return=to_float_safe(h.post_listing_30d_return),
                post_listing_90d_return=to_float_safe(h.post_listing_90d_return),
                post_listing_180d_return=to_float_safe(h.post_listing_180d_return),
                post_listing_1y_return=to_float_safe(h.post_listing_1y_return),
                max_upside_from_issue_price=to_float_safe(h.max_upside_from_issue_price),
                max_drawdown_from_issue_price=to_float_safe(h.max_drawdown_from_issue_price),
                source_id=primary_source_id,
            )

        # 13. Performance Events Mapping
        event_models: List[PerformanceEventModel] = []
        for pe in record.performance_events:
            event_models.append(
                PerformanceEventModel(
                    ipo_id=ipo_id,
                    event_date=parse_date_safe(pe.event_date) or date.today(),
                    event_type=pe.event_type.value if isinstance(pe.event_type, PerformanceEventTypeEnum) else str(pe.event_type),
                    reference_price=pe.reference_price,
                    market_price=pe.market_price,
                    return_percentage=pe.return_percentage,
                    days_from_listing=pe.days_from_listing,
                    reached_40_percent_target=pe.reached_40_percent_target,
                    source_id=primary_source_id,
                )
            )

        return {
            "master": master_model,
            "sources": sources_models,
            "objects_of_issue": objects_models,
            "financials": financial_models,
            "valuation": valuation_model,
            "subscriptions": subscription_models,
            "anchor_header": anchor_header_model,
            "anchor_investors": anchor_investor_models,
            "gmp_logs": gmp_models,
            "peers": peer_models,
            "risks": risk_models,
            "scenario": scenario_model,
            "historical_performance": hist_model,
            "performance_events": event_models,
        }

    @classmethod
    def models_to_record(
        cls,
        master_model: IPOMasterModel,
        related_models: Optional[Dict[str, Any]] = None,
    ) -> MasterIPORecord:
        """
        Maps an IPOMasterModel and associated child models back into a domain MasterIPORecord.

        Args:
            master_model: Primary IPOMasterModel instance.
            related_models: Optional dictionary of child model lists/instances.

        Returns:
            Fully populated, strongly-typed MasterIPORecord instance.
        """
        rel = related_models or {}

        # 1. IPO Entity & Status
        entity = IPOEntity(
            ipo_id=master_model.ipo_id,
            company_name=master_model.company_name,
            company_legal_name=master_model.company_legal_name,
            ticker_symbol=master_model.ticker_symbol or "",
            isin=master_model.isin or "",
            segment=SegmentEnum(master_model.segment) if master_model.segment in SegmentEnum._value2member_map_ else SegmentEnum.MAINBOARD,
            sector=master_model.sector,
            industry=master_model.industry,
        )

        open_d_str = format_date_safe(master_model.open_date) or ""
        close_d_str = format_date_safe(master_model.close_date) or ""
        list_d_str = format_date_safe(master_model.listing_date) or ""

        allot_d_str = format_date_safe(getattr(master_model, "allotment_date", None))
        if not allot_d_str and close_d_str:
            try:
                from datetime import datetime as dt_cls, timedelta as td_cls
                cd = dt_cls.strptime(close_d_str, "%Y-%m-%d").date()

                # Validate whether existing list_d_str is strictly after close_date
                ld = None
                if list_d_str:
                    try:
                        parsed_ld = dt_cls.strptime(list_d_str, "%Y-%m-%d").date()
                        if parsed_ld > cd:
                            ld = parsed_ld
                    except Exception:
                        pass

                # If missing or invalid (<= cd), derive SEBI T+3 trading day listing date
                if not ld:
                    cur = cd
                    added = 0
                    while added < 3:
                        cur += td_cls(days=1)
                        if cur.weekday() < 5:
                            added += 1
                    ld = cur
                    list_d_str = ld.isoformat()

                # Derive SEBI T+1 working day basis of allotment date
                cur = cd
                added = 0
                while added < 1:
                    cur += td_cls(days=1)
                    if cur.weekday() < 5:
                        added += 1
                ad = cur
                if ad >= ld:
                    ad = ld - td_cls(days=1)
                allot_d_str = ad.isoformat()
            except Exception:
                allot_d_str = None

        status = IPOStatus(
            status=IPOStatusEnum(master_model.status) if master_model.status in IPOStatusEnum._value2member_map_ else IPOStatusEnum.UPCOMING,
            research_date=format_date_safe(master_model.research_date) or "",
            research_time=format_time_safe(master_model.research_time) or "",
            data_cutoff=format_datetime_safe(master_model.data_cutoff) or "",
            open_date=open_d_str,
            close_date=close_d_str,
            listing_date=list_d_str,
            listing_status=ListingStatusEnum(master_model.listing_status) if master_model.listing_status in ListingStatusEnum._value2member_map_ else ListingStatusEnum.PRE_LISTING,
            allotment_date=allot_d_str,
        )

        # 2. Issue Structure (Provenance Envelope Reconstruction)
        issue_structure = IssueStructure(
            issue_size=build_provenance_envelope(master_model.issue_size, unit="Cr"),
            fresh_issue_amount=build_provenance_envelope(master_model.fresh_issue_amount, unit="Cr"),
            ofs_amount=build_provenance_envelope(master_model.ofs_amount, unit="Cr"),
            fresh_issue_percentage=build_provenance_envelope(master_model.fresh_issue_percentage, unit="%"),
            ofs_percentage=build_provenance_envelope(master_model.ofs_percentage, unit="%"),
            face_value=build_provenance_envelope(master_model.face_value, unit="INR"),
            price_band_low=build_provenance_envelope(master_model.price_band_low, unit="INR"),
            price_band_high=build_provenance_envelope(master_model.price_band_high, unit="INR"),
            issue_price=build_provenance_envelope(master_model.issue_price, unit="INR"),
            lot_size=build_provenance_envelope(master_model.lot_size, unit="Shares"),
            minimum_investment=build_provenance_envelope(master_model.minimum_investment, unit="INR"),
            employee_reservation=build_provenance_envelope(master_model.employee_reservation, unit="INR") if master_model.employee_reservation else None,
            shareholder_reservation=build_provenance_envelope(master_model.shareholder_reservation, unit="INR") if master_model.shareholder_reservation else None,
            other_reservation=build_provenance_envelope(master_model.other_reservation, unit="INR") if master_model.other_reservation else None,
        )

        # 3. Valuation Data
        val_model: Optional[ValuationModel] = rel.get("valuation")
        if val_model:
            valuation_data = ValuationData(
                reference_price=to_float_safe(val_model.issue_price) or 0.0,
                reference_eps=to_float_safe(val_model.reference_eps) or 0.0,
                issue_pe=build_provenance_envelope(to_float_safe(val_model.issue_pe) or 0.0, data_type=DataTypeEnum.CALCULATED),
                valuation_method=val_model.valuation_method or "Relative PE",
                valuation_source=val_model.valuation_source or "RHP",
                valuation_date=format_date_safe(val_model.valuation_date) or "",
                issue_pb=build_provenance_envelope(to_float_safe(val_model.issue_pb)) if val_model.issue_pb else None,
                industry_pe=build_provenance_envelope(to_float_safe(val_model.industry_pe)) if val_model.industry_pe else None,
                industry_pb=build_provenance_envelope(to_float_safe(val_model.industry_pb)) if val_model.industry_pb else None,
                peer_average_pe=build_provenance_envelope(to_float_safe(val_model.peer_average_pe)) if val_model.peer_average_pe else None,
                peer_average_pb=build_provenance_envelope(to_float_safe(val_model.peer_average_pb)) if val_model.peer_average_pb else None,
                reference_book_value_per_share=to_float_safe(val_model.reference_book_value_per_share),
            )
        else:
            valuation_data = ValuationData(
                reference_price=to_float_safe(master_model.price_band_high) or 0.0,
                reference_eps=0.0,
                issue_pe=build_provenance_envelope(0.0),
                valuation_method="Not available",
                valuation_source="Not available",
                valuation_date=format_date_safe(master_model.research_date) or "",
            )

        # 4. Objects of Issue
        objects_of_issue: List[ObjectOfIssue] = []
        for obj_m in rel.get("objects_of_issue", []):
            disc_status = (
                ObjectsDisclosureStatusEnum(obj_m.disclosure_status)
                if obj_m.disclosure_status in ObjectsDisclosureStatusEnum._value2member_map_
                else ObjectsDisclosureStatusEnum.DISCLOSED
            )
            objects_of_issue.append(
                ObjectOfIssue(
                    purpose=obj_m.purpose_description,
                    amount=obj_m.amount,
                    source="RHP",
                    source_date=format_date_safe(master_model.research_date) or "",
                    percentage_of_fresh_issue=obj_m.percentage_of_fresh_issue,
                    disclosure_status=disc_status,
                )
            )

        # 5. Financial Records
        financial_data: List[FinancialRecord] = []
        for fin_m in rel.get("financials", []):
            p_type = PeriodTypeEnum(fin_m.period_type) if fin_m.period_type in PeriodTypeEnum._value2member_map_ else PeriodTypeEnum.FY
            financial_data.append(
                FinancialRecord(
                    financial_period=fin_m.financial_period,
                    period_type=p_type,
                    revenue=build_provenance_envelope(fin_m.revenue, unit="Cr") if fin_m.revenue is not None else None,
                    revenue_growth=build_provenance_envelope(fin_m.revenue_growth, unit="%") if fin_m.revenue_growth is not None else None,
                    EBITDA=build_provenance_envelope(fin_m.EBITDA, unit="Cr") if fin_m.EBITDA is not None else None,
                    EBITDA_margin=build_provenance_envelope(fin_m.EBITDA_margin, unit="%") if fin_m.EBITDA_margin is not None else None,
                    PAT=build_provenance_envelope(fin_m.PAT, unit="Cr") if fin_m.PAT is not None else None,
                    PAT_growth=build_provenance_envelope(fin_m.PAT_growth, unit="%") if fin_m.PAT_growth is not None else None,
                    EPS=build_provenance_envelope(fin_m.EPS, unit="INR") if fin_m.EPS is not None else None,
                    book_value_per_share=build_provenance_envelope(fin_m.book_value_per_share, unit="INR") if fin_m.book_value_per_share is not None else None,
                    ROE=build_provenance_envelope(fin_m.ROE, unit="%") if fin_m.ROE is not None else None,
                    ROCE=build_provenance_envelope(fin_m.ROCE, unit="%") if fin_m.ROCE is not None else None,
                    total_debt=build_provenance_envelope(fin_m.total_debt, unit="Cr") if fin_m.total_debt is not None else None,
                    net_debt=build_provenance_envelope(fin_m.net_debt, unit="Cr") if fin_m.net_debt is not None else None,
                    debt_equity=build_provenance_envelope(fin_m.debt_equity, unit="x") if fin_m.debt_equity is not None else None,
                    operating_cash_flow=build_provenance_envelope(fin_m.operating_cash_flow, unit="Cr") if fin_m.operating_cash_flow is not None else None,
                    investing_cash_flow=build_provenance_envelope(fin_m.investing_cash_flow, unit="Cr") if fin_m.investing_cash_flow is not None else None,
                    financing_cash_flow=build_provenance_envelope(fin_m.financing_cash_flow, unit="Cr") if fin_m.financing_cash_flow is not None else None,
                    free_cash_flow=build_provenance_envelope(fin_m.free_cash_flow, unit="Cr") if fin_m.free_cash_flow is not None else None,
                )
            )

        # 6. Subscription Data
        subscription_data: Dict[str, SubscriptionCategory] = {}
        sub_models: List[SubscriptionModel] = rel.get("subscriptions", [])
        if sub_models:
            sub_m = sub_models[0]
            s_date = format_date_safe(sub_m.subscription_date) or ""
            r_time = format_datetime_safe(sub_m.retrieval_timestamp) or ""

            if sub_m.QIB_shares_offered is not None:
                subscription_data["QIB"] = SubscriptionCategory(
                    shares_offered=sub_m.QIB_shares_offered,
                    shares_bid=sub_m.QIB_shares_bid or 0,
                    subscription_multiple=sub_m.QIB_subscription_multiple or 0.0,
                    source="Exchange",
                    source_date=s_date,
                    retrieval_timestamp=r_time,
                )
            if sub_m.NII_total_shares_offered is not None:
                subscription_data["NII"] = SubscriptionCategory(
                    shares_offered=sub_m.NII_total_shares_offered,
                    shares_bid=sub_m.NII_total_shares_bid or 0,
                    subscription_multiple=sub_m.NII_total_subscription_multiple or 0.0,
                    source="Exchange",
                    source_date=s_date,
                    retrieval_timestamp=r_time,
                )
            if sub_m.retail_shares_offered is not None:
                subscription_data["Retail"] = SubscriptionCategory(
                    shares_offered=sub_m.retail_shares_offered,
                    shares_bid=sub_m.retail_shares_bid or 0,
                    subscription_multiple=sub_m.retail_subscription_multiple or 0.0,
                    source="Exchange",
                    source_date=s_date,
                    retrieval_timestamp=r_time,
                )
            if getattr(sub_m, "total_subscription", None) is not None:
                subscription_data["Total"] = SubscriptionCategory(
                    shares_offered=0,
                    shares_bid=0,
                    subscription_multiple=float(sub_m.total_subscription),
                    source="Exchange",
                    source_date=s_date,
                    retrieval_timestamp=r_time,
                )

        # 7. Anchor Data
        anchor_data: Optional[AnchorData] = None
        anc_hdr: Optional[AnchorHeaderModel] = rel.get("anchor_header")
        if anc_hdr:
            investors: List[AnchorInvestor] = []
            for inv_m in rel.get("anchor_investors", []):
                inv_type = InvestorTypeEnum(inv_m.investor_type) if inv_m.investor_type in InvestorTypeEnum._value2member_map_ else InvestorTypeEnum.OTHER
                investors.append(
                    AnchorInvestor(
                        investor_name=inv_m.investor_name,
                        investor_type=inv_type,
                        allocation_amount=inv_m.allocation_amount,
                        allocation_shares=inv_m.allocation_shares,
                        allocation_percentage=inv_m.allocation_percentage or 0.0,
                        source="RHP Anchor List",
                        source_date=format_date_safe(anc_hdr.source_date) or "",
                    )
                )

            anchor_data = AnchorData(
                anchor_allocation=anc_hdr.anchor_allocation,
                anchor_price=anc_hdr.anchor_price,
                anchor_investor_count=anc_hdr.anchor_investor_count,
                anchor_allocation_percentage=anc_hdr.anchor_allocation_percentage or 0.0,
                lock_in_30_day=format_date_safe(anc_hdr.lock_in_30_day) or "",
                lock_in_90_day=format_date_safe(anc_hdr.lock_in_90_day) or "",
                anchor_investors=investors,
            )

        # 8. GMP Data
        gmp_data: Optional[GMPData] = None
        gmp_models: List[GMPLogModel] = rel.get("gmp_logs", [])
        if gmp_models:
            gmp_m = gmp_models[0]
            stype = SourceTypeEnum(gmp_m.source_type) if gmp_m.source_type in SourceTypeEnum._value2member_map_ else SourceTypeEnum.UNOFFICIAL_GMP
            gmp_data = GMPData(
                gmp_value=to_float_safe(gmp_m.gmp_value) or 0.0,
                gmp_percentage=to_float_safe(gmp_m.gmp_percentage) or 0.0,
                gmp_date=format_date_safe(gmp_m.gmp_date) or "",
                gmp_time=format_time_safe(gmp_m.gmp_time) or "",
                reference_price=to_float_safe(gmp_m.reference_price) or 0.0,
                implied_price=to_float_safe(gmp_m.implied_price) or 0.0,
                source="Market Tracker",
                source_type=stype,
            )

        # 9. Peer Companies
        peer_companies: List[PeerCompany] = []
        for peer_m in rel.get("peers", []):
            peer_companies.append(
                PeerCompany(
                    company_name=peer_m.peer_company_name,
                    ticker=peer_m.ticker,
                    source="RHP Peer Comparison",
                    source_date=format_date_safe(master_model.research_date) or "",
                    market_cap=peer_m.market_cap,
                    revenue=peer_m.revenue,
                    PAT=peer_m.PAT,
                    EPS=peer_m.EPS,
                    PE=peer_m.PE,
                    PB=peer_m.PB,
                    ROE=peer_m.ROE,
                    ROCE=peer_m.ROCE,
                    debt_equity=peer_m.debt_equity,
                )
            )

        # 10. Risk Data
        risk_data: List[RiskRecord] = []
        for r_m in rel.get("risks", []):
            rcat = RiskCategoryEnum(r_m.risk_type) if r_m.risk_type in RiskCategoryEnum._value2member_map_ else RiskCategoryEnum.INTERNAL
            rsev = RiskSeverityEnum(r_m.severity) if r_m.severity in RiskSeverityEnum._value2member_map_ else RiskSeverityEnum.MEDIUM
            risk_data.append(
                RiskRecord(
                    risk_category=rcat,
                    risk_description=r_m.risk_description,
                    severity=rsev,
                    source="RHP Risk Factors",
                    source_date=format_date_safe(master_model.research_date) or "",
                )
            )

        # 11. Scenario 40 Percent
        scen_m: Optional[ScenarioModel] = rel.get("scenario")
        if scen_m:
            supporting = json.loads(scen_m.supporting_factors) if scen_m.supporting_factors else []
            contradictory = json.loads(scen_m.contradictory_factors) if scen_m.contradictory_factors else []
            scen_status = ScenarioStatusEnum(scen_m.scenario_status) if scen_m.scenario_status in ScenarioStatusEnum._value2member_map_ else ScenarioStatusEnum.INSUFFICIENT_EVIDENCE

            scenario_40_percent = Scenario40Percent(
                reference_price=to_float_safe(scen_m.reference_price) or 0.0,
                target_price=to_float_safe(scen_m.target_price) or 0.0,
                supporting_factors=supporting,
                contradictory_factors=contradictory,
                scenario_status=scen_status,
                scenario_methodology=scen_m.scenario_methodology,
                scenario_data_timestamp=format_datetime_safe(scen_m.scenario_data_timestamp) or "",
                required_price_movement=to_float_safe(scen_m.required_price_movement) or 40.0,
                target_pe=to_float_safe(scen_m.target_pe),
                target_pb=to_float_safe(scen_m.target_pb),
            )
        else:
            ref_p = to_float_safe(master_model.price_band_high) or 0.0
            scenario_40_percent = Scenario40Percent(
                reference_price=ref_p,
                target_price=round(ref_p * 1.40, 2),
                supporting_factors=[],
                contradictory_factors=[],
                scenario_status=ScenarioStatusEnum.INSUFFICIENT_EVIDENCE,
                scenario_methodology="Standardized +40% target hypothesis",
                scenario_data_timestamp=format_datetime_safe(master_model.data_cutoff) or "",
            )

        # 12. Sources
        sources: List[SourceRecord] = []
        for src_m in rel.get("sources", []):
            stype = SourceTypeEnum(src_m.source_type) if src_m.source_type in SourceTypeEnum._value2member_map_ else SourceTypeEnum.RHP
            dtype = DataTypeEnum(src_m.data_type) if src_m.data_type in DataTypeEnum._value2member_map_ else DataTypeEnum.REPORTED
            sources.append(
                SourceRecord(
                    source_name=src_m.source_name,
                    source_type=stype,
                    source_url=src_m.source_url,
                    publication_date=format_date_safe(src_m.publication_date),
                    retrieval_timestamp=format_datetime_safe(src_m.retrieval_timestamp),
                    page_or_section=src_m.page_or_section,
                    data_type=dtype,
                    notes=src_m.notes,
                )
            )

        # 13. Historical Performance
        historical_ipo: Optional[HistoricalIPO] = None
        hist_m: Optional[HistoricalPerformanceModel] = rel.get("historical_performance")
        if hist_m:
            historical_ipo = HistoricalIPO(
                historical_ipo=True,
                ipo_year=hist_m.ipo_year,
                listing_price=hist_m.listing_price,
                listing_day_close=hist_m.listing_day_close,
                listing_day_high=hist_m.listing_day_high or "Not available",
                listing_day_low=hist_m.listing_day_low or "Not available",
                listing_day_return=hist_m.listing_day_return,
                post_listing_7d_return=hist_m.post_listing_7d_return or "Not available",
                post_listing_30d_return=hist_m.post_listing_30d_return or "Not available",
                post_listing_90d_return=hist_m.post_listing_90d_return or "Not available",
                post_listing_180d_return=hist_m.post_listing_180d_return or "Not available",
                post_listing_1y_return=hist_m.post_listing_1y_return or "Not available",
                max_upside_from_issue_price=hist_m.max_upside_from_issue_price or "Not available",
                max_drawdown_from_issue_price=hist_m.max_drawdown_from_issue_price or "Not available",
            )

        # 14. Performance Events
        performance_events: List[PerformanceEvent] = []
        for pe_m in rel.get("performance_events", []):
            etype = PerformanceEventTypeEnum(pe_m.event_type) if pe_m.event_type in PerformanceEventTypeEnum._value2member_map_ else PerformanceEventTypeEnum.LISTING
            performance_events.append(
                PerformanceEvent(
                    event_date=format_date_safe(pe_m.event_date) or "",
                    event_type=etype,
                    reference_price=pe_m.reference_price,
                    market_price=pe_m.market_price,
                    return_percentage=pe_m.return_percentage,
                    days_from_listing=pe_m.days_from_listing,
                    reached_40_percent_target=pe_m.reached_40_percent_target,
                    source="Exchange Data",
                )
            )

        data_quality = DataQuality(
            completeness_status=DataCompletenessEnum.COMPLETE,
            source_verification_status=SourceVerificationEnum.VERIFIED,
            last_verified=format_date_safe(master_model.research_date) or "",
            notes="Reconstructed from database ORM persistence.",
        )

        return MasterIPORecord(
            ipo_entity=entity,
            ipo_status=status,
            issue_structure=issue_structure,
            valuation_data=valuation_data,
            scenario_40_percent=scenario_40_percent,
            data_quality=data_quality,
            schema_version="1.0",
            objects_of_issue=objects_of_issue,
            financial_data=financial_data,
            subscription_data=subscription_data,
            anchor_data=anchor_data,
            gmp_data=gmp_data,
            peer_companies=peer_companies,
            risk_data=risk_data,
            sources=sources,
            historical_ipo=historical_ipo,
            performance_events=performance_events,
        )
