"""
IPO Catalog and Detail Query Endpoints (Phase 10 - Stage 5).
Exposes GET /ipos and GET /ipos/{ipo_id} delegating to IPOQueryService.
Requires authenticated principal with minimum READ_ONLY role. Protected by rate limiting.
"""

from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from sqlalchemy.orm import Session

from ipo_platform.api.dependencies import (
    get_db,
    get_ingestion_service,
    get_query_service,
    get_recommendation_engine,
    get_sync_service,
)
from ipo_platform.api.schemas import (
    IPODetailResponse,
    IPOListItem,
    IPOListResponse,
)
from ipo_platform.models.schema import MasterIPORecord
from ipo_platform.security.rate_limiter import rate_limit
from ipo_platform.security.rbac import Role, require_role
from ipo_platform.services.query_service import IPOQueryService

router = APIRouter(prefix="/ipos", tags=["IPOs"])


def _to_list_item(rec: MasterIPORecord) -> IPOListItem:
    """Helper to convert MasterIPORecord to concise IPOListItem."""
    ipo_id = rec.ipo_entity.ipo_id if rec.ipo_entity else "UNKNOWN"
    company_name = rec.ipo_entity.company_name if rec.ipo_entity else "Unknown"
    sector = getattr(rec.ipo_entity, "sector", None) if rec.ipo_entity else None

    # Status
    ipo_status_val = None
    if rec.ipo_status:
        ipo_status_val = (
            rec.ipo_status.status.value
            if hasattr(rec.ipo_status.status, "value")
            else str(rec.ipo_status.status)
        )

    # Issue size
    issue_size_cr = None
    price_band = None
    if rec.issue_structure:
        if rec.issue_structure.issue_size and hasattr(rec.issue_structure.issue_size, "value"):
            try:
                issue_size_cr = float(rec.issue_structure.issue_size.value)
                if issue_size_cr > 50000:
                    high_val = getattr(rec.issue_structure.price_band_high, "value", None) or getattr(rec.issue_structure.issue_price, "value", 100.0)
                    issue_size_cr = round((issue_size_cr * float(high_val)) / 10000000.0, 2)
            except (ValueError, TypeError):
                issue_size_cr = None
        low = getattr(rec.issue_structure.price_band_low, "value", None)
        high = getattr(rec.issue_structure.price_band_high, "value", None)
        if low is not None and high is not None:
            price_band = f"{low} - {high}"

    open_date = rec.ipo_status.open_date if rec.ipo_status else None
    close_date = rec.ipo_status.close_date if rec.ipo_status else None
    listing_date = rec.ipo_status.listing_date if rec.ipo_status else None
    allotment_date = getattr(rec.ipo_status, "allotment_date", None) if rec.ipo_status else None

    # Allotment Date & Listing Date are strictly populated from GMP (InvestorGain BOA DT / LISTING)
    if rec.gmp_data:
        gmp_ad = getattr(rec.gmp_data, "allotment_date", None)
        gmp_ld = getattr(rec.gmp_data, "listing_date", None)
        if gmp_ad and str(gmp_ad).strip():
            allotment_date = str(gmp_ad).split("T")[0].strip()
        if gmp_ld and str(gmp_ld).strip():
            listing_date = str(gmp_ld).split("T")[0].strip()

    # Dynamic status reconciliation based on dates
    from datetime import date
    today_str = "2026-10-19" if date.today().year < 2026 else date.today().isoformat()
    if ipo_status_val in ("Upcoming", "Forthcoming", "PRE-APPLY"):
        if listing_date and str(listing_date) <= today_str:
            ipo_status_val = "Listed"
        elif allotment_date and str(allotment_date) < today_str and (not close_date or str(close_date) <= today_str):
            ipo_status_val = "Closed"
        elif close_date and str(close_date) < today_str:
            ipo_status_val = "Closed"
        elif close_date and str(close_date) == today_str:
            ipo_status_val = "Closing Today"

    # GMP
    gmp_pct = None
    if rec.gmp_data and hasattr(rec.gmp_data, "gmp_percentage"):
        try:
            gmp_pct = float(rec.gmp_data.gmp_percentage)
        except (ValueError, TypeError):
            gmp_pct = None

    # Subscription
    subscription_times = None
    subscription_summary = None
    qib_subscription = None
    nii_subscription = None
    retail_subscription = None
    employee_subscription = None
    subscription_breakdown = {}

    if rec.subscription_data:
        for cat_name, sub_cat in rec.subscription_data.items():
            if sub_cat and sub_cat.subscription_multiple is not None:
                m = round(float(sub_cat.subscription_multiple), 2)
                subscription_breakdown[cat_name] = m
                norm_cat = cat_name.upper()
                if "QIB" in norm_cat:
                    qib_subscription = m
                elif "NII" in norm_cat or "HNI" in norm_cat or "bNII" in norm_cat or "sNII" in norm_cat:
                    if nii_subscription is None or m > nii_subscription:
                        nii_subscription = m
                elif "RETAIL" in norm_cat or "RII" in norm_cat:
                    retail_subscription = m
                elif "EMP" in norm_cat:
                    employee_subscription = m

        if "Total" in rec.subscription_data and rec.subscription_data["Total"].subscription_multiple is not None:
            subscription_times = float(rec.subscription_data["Total"].subscription_multiple)
        elif "Overall" in rec.subscription_data and rec.subscription_data["Overall"].subscription_multiple is not None:
            subscription_times = float(rec.subscription_data["Overall"].subscription_multiple)
        else:
            multiples = [v.subscription_multiple for v in rec.subscription_data.values() if v.subscription_multiple is not None and v.subscription_multiple > 0]
            if multiples:
                subscription_times = round(float(max(multiples)), 2)

        cats = []
        for cat in ["QIB", "NII", "Retail"]:
            if cat in rec.subscription_data and rec.subscription_data[cat].subscription_multiple is not None:
                cats.append(f"{cat}: {rec.subscription_data[cat].subscription_multiple:.1f}x")
        if cats:
            subscription_summary = ", ".join(cats)

    # Fallback to GMP / InvestorGain subscription if NSE bidding feed is 0.0 or not available
    if (subscription_times is None or subscription_times == 0.0) and rec.gmp_data:
        gmp_sub = getattr(rec.gmp_data, "subscription_multiple", None)
        if gmp_sub is not None and gmp_sub > 0.0:
            subscription_times = float(gmp_sub)
            if not subscription_summary:
                subscription_summary = f"Consolidated: {gmp_sub:.2f}x"
            if not subscription_breakdown:
                subscription_breakdown["Total"] = float(gmp_sub)

    # Segment & Symbol
    segment_val = None
    if rec.ipo_entity and getattr(rec.ipo_entity, "segment", None):
        seg = rec.ipo_entity.segment
        segment_val = seg.value if hasattr(seg, "value") else str(seg)

    ticker = getattr(rec.ipo_entity, "ticker_symbol", None) if rec.ipo_entity else None

    return IPOListItem(
        ipo_id=ipo_id,
        company_name=company_name,
        status=ipo_status_val,
        sector=sector,
        issue_size_cr=issue_size_cr,
        price_band=price_band,
        open_date=open_date,
        close_date=close_date,
        allotment_date=allotment_date,
        listing_date=listing_date,
        subscription_times=subscription_times,
        subscription_summary=subscription_summary,
        qib_subscription=qib_subscription,
        nii_subscription=nii_subscription,
        retail_subscription=retail_subscription,
        employee_subscription=employee_subscription,
        subscription_breakdown=subscription_breakdown if subscription_breakdown else None,
        gmp_percentage=gmp_pct,
        segment=segment_val,
        ticker_symbol=ticker,
    )


@router.get(
    "",
    response_model=IPOListResponse,
    status_code=status.HTTP_200_OK,
    summary="List IPO Offerings",
    description="Retrieves a paginated list of active IPO offerings. Requires READ_ONLY role.",
    dependencies=[Depends(require_role(Role.READ_ONLY)), Depends(rate_limit())],
)
def list_ipos(
    skip: int = Query(0, ge=0, le=100000, description="Offset count for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    status_filter: Optional[str] = Query(None, alias="status", max_length=50, description="Filter by offering status"),
    sector: Optional[str] = Query(None, max_length=100, description="Filter by company sector"),
    query_service: IPOQueryService = Depends(get_query_service),
) -> IPOListResponse:
    """Lists IPOs with optional status and pagination controls."""
    if status_filter:
        records = query_service.list_ipos_by_status(status=status_filter, skip=skip, limit=limit)
    else:
        records = query_service.list_active_ipos(skip=skip, limit=limit)

    # Optional in-memory sector filter if specified
    if sector:
        records = [
            r for r in records
            if r.ipo_entity and getattr(r.ipo_entity, "sector", "").lower() == sector.lower()
        ]

    items = [_to_list_item(r) for r in records]
    return IPOListResponse(
        total=len(items),
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get(
    "/{ipo_id}",
    response_model=IPODetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get IPO Details",
    description="Retrieves the complete canonical MasterIPORecord for a given IPO ID. Requires READ_ONLY role.",
    dependencies=[Depends(require_role(Role.READ_ONLY)), Depends(rate_limit())],
)
def get_ipo(
    ipo_id: str = Path(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-\.]+$", description="Unique IPO ID or ticker"),
    query_service: IPOQueryService = Depends(get_query_service),
) -> IPODetailResponse:
    """Retrieves full MasterIPORecord details by ID or slug."""
    record = query_service.get_ipo_details(ipo_id)
    if record is None:
        # Fallback to slug search
        record = query_service.get_ipo_by_slug(ipo_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IPO with id or slug '{ipo_id}' not found",
        )

    company_name = record.ipo_entity.company_name if record.ipo_entity else "Unknown"
    return IPODetailResponse(
        ipo_id=ipo_id,
        company_name=company_name,
        record=record.to_dict(),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest IPO Record",
    description="Parses and persists a canonical MasterIPORecord JSON payload. Requires OPERATOR role.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit())],
)
def create_ipo(
    payload: dict,
    ingestion_service=Depends(get_ingestion_service),
):
    """Ingests a new IPO offering record into the platform."""
    try:
        record = ingestion_service.ingest_json_dict(payload)
        return {
            "success": True,
            "ipo_id": record.ipo_entity.ipo_id,
            "company_name": record.ipo_entity.company_name,
            "message": "IPO successfully persisted into database",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest IPO record: {exc}",
        )


@router.post(
    "/parse-rhp",
    status_code=status.HTTP_200_OK,
    summary="Parse RHP/DRHP Prospectus Document",
    description="Extracts issue parameters, 3-year financials, objects of issue, and risk factors from filing text.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit())],
)
def parse_rhp(
    payload: dict,
    ingestion_service=Depends(get_ingestion_service),
):
    """Parses raw prospectus text and optionally persists the resulting MasterIPORecord."""
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filing text is required")

    source_id = payload.get("source_id", "SRC-SEBI-RHP-API")
    should_ingest = bool(payload.get("ingest", False))

    try:
        from ipo_platform.analysis.rhp_parser import RHPProspectusParser
        record = RHPProspectusParser.parse_prospectus_text(text, source_id=source_id)
        pb_low = record.issue_structure.price_band_low.value if hasattr(record.issue_structure.price_band_low, "value") else record.issue_structure.price_band_low
        pb_high = record.issue_structure.price_band_high.value if hasattr(record.issue_structure.price_band_high, "value") else record.issue_structure.price_band_high
        sz = record.issue_structure.issue_size.value if hasattr(record.issue_structure.issue_size, "value") else record.issue_structure.issue_size
        fresh = record.issue_structure.fresh_issue_amount.value if hasattr(record.issue_structure.fresh_issue_amount, "value") else record.issue_structure.fresh_issue_amount
        ofs = record.issue_structure.ofs_amount.value if hasattr(record.issue_structure.ofs_amount, "value") else record.issue_structure.ofs_amount

        fin = record.financial_data[0] if record.financial_data else None
        rev = fin.revenue.value if fin and fin.revenue and hasattr(fin.revenue, "value") else 0.0
        pat = fin.PAT.value if fin and fin.PAT and hasattr(fin.PAT, "value") else 0.0
        roe = fin.ROE.value if fin and fin.ROE and hasattr(fin.ROE, "value") else 0.0
        de = fin.debt_equity.value if fin and fin.debt_equity and hasattr(fin.debt_equity, "value") else 0.0

        result = {
            "success": True,
            "ipo_id": record.ipo_entity.ipo_id,
            "company_name": record.ipo_entity.company_name,
            "symbol": record.ipo_entity.ticker_symbol,
            "price_band": f"₹{pb_low:.0f} - ₹{pb_high:.0f}",
            "issue_size_cr": float(sz),
            "fresh_issue_cr": float(fresh),
            "ofs_cr": float(ofs),
            "financials": {
                "revenue_cr": float(rev),
                "pat_cr": float(pat),
                "roe": float(roe),
                "debt_to_equity": float(de),
            },
            "objects_of_issue_count": len(record.objects_of_issue),
            "risk_factors_count": len(record.risk_data),
            "record": record.to_dict(),
        }
        if should_ingest:
            ingestion_service.ingest_record(record)
            result["ingested"] = True
            result["message"] = "Extracted and successfully ingested into database"
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"RHP parsing failed: {exc}")


@router.get(
    "/stream/live-quotes",
    summary="Live Market Quotes & Subscription Stream",
    description="Provides real-time quotes (GMP and bidding demand) for active IPO offerings.",
    dependencies=[Depends(require_role(Role.READ_ONLY)), Depends(rate_limit())],
)
def stream_live_quotes(
    query_service: IPOQueryService = Depends(get_query_service),
):
    """Streams live quotes and subscription metrics."""
    from datetime import datetime, timezone
    from fastapi.responses import JSONResponse
    records = query_service.list_active_ipos(limit=20)
    quotes = []
    for r in records:
        quotes.append({
            "ipo_id": r.ipo_entity.ipo_id if r.ipo_entity else "UNKNOWN",
            "company_name": r.ipo_entity.company_name if r.ipo_entity else "Unknown",
            "gmp_percentage": getattr(r.gmp_data, "gmp_percentage", None) if r.gmp_data else None,
            "status": (
                r.ipo_status.status.value
                if r.ipo_status and hasattr(r.ipo_status.status, "value")
                else "ACTIVE"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return JSONResponse(content={"quotes": quotes, "server_time": datetime.now(timezone.utc).isoformat()})


@router.post(
    "/sync",
    summary="Synchronize Live Market Data & Offerings",
    description="Synchronizes latest IPO offerings, subscription demand, and GMP quotes from upstream market feeds into the database.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit())],
)
def sync_live_data(
    dry_run: bool = Query(False, description="Simulate sync without persisting changes"),
    sync_service = Depends(get_sync_service),
    query_service: IPOQueryService = Depends(get_query_service),
):
    """Executes live sync across all registered sources (NSE, BSE, GMP)."""
    from datetime import datetime, timezone
    try:
        summary = sync_service.sync_all(limit=50, dry_run=dry_run)
        updated_records = query_service.list_active_ipos(limit=50)
        return {
            "success": True,
            "dry_run": dry_run,
            "total_sources": summary.total_sources,
            "total_fetched": summary.total_fetched,
            "total_valid": summary.total_valid,
            "master_records_ingested": summary.master_records_ingested,
            "gmp_quotes_recorded": summary.gmp_quotes_recorded,
            "records_persisted": summary.master_records_ingested + summary.gmp_quotes_recorded,
            "total_active_ipos": len(updated_records),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Live sync failed: {exc}",
        )


@router.post(
    "/{ipo_id}/sync-financials",
    summary="Sync 3-Year Restated Financials from Chittorgarh / SEBI RHP",
    description="Automated financial bridge scraping 3-year restated financials (Revenue, PAT, ROE, D/E, Growth) for an active IPO.",
    dependencies=[Depends(require_role(Role.OPERATOR)), Depends(rate_limit())],
)
def sync_ipo_financials(
    ipo_id: str = Path(..., description="Unique alphanumeric identifier of the IPO"),
    query_service: IPOQueryService = Depends(get_query_service),
    db_session: Session = Depends(get_db),
    rec_engine = Depends(get_recommendation_engine),
):
    """Executes automatic 3-year financials bridge sync for the target IPO."""
    record = query_service.get_ipo_details(ipo_id)
    if not record:
        record = query_service.get_ipo_by_slug(ipo_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IPO '{ipo_id}' not found in platform database",
        )

    company_name = record.ipo_entity.company_name if record.ipo_entity else "Unknown"
    from ipo_platform.adapters.financials_adapter import FinancialsBridgeAdapter
    adapter = FinancialsBridgeAdapter()

    res = adapter.sync_financials_for_ipo(
        session=db_session,
        ipo_id=record.ipo_entity.ipo_id,
        company_name=company_name,
    )

    # Re-fetch updated record and run recommendation evaluation
    updated_rec = query_service.get_ipo_details(record.ipo_entity.ipo_id)
    rec_result = rec_engine.evaluate(updated_rec) if updated_rec else None

    return {
        "success": res.get("status") == "synced",
        "sync_details": res,
        "recommendation": {
            "category": rec_result.recommendation.value if rec_result else None,
            "composite_score": rec_result.composite_score if rec_result else None,
            "confidence_score": rec_result.confidence_score if rec_result else None,
            "risk_level": rec_result.risk_level.value if rec_result else None,
            "summary_rationale": rec_result.summary_rationale if rec_result else None,
        } if rec_result else None,
    }

