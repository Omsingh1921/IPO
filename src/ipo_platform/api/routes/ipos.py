"""
IPO Catalog and Detail Query Endpoints (Phase 10 - Stage 5).
Exposes GET /ipos and GET /ipos/{ipo_id} delegating to IPOQueryService.
Requires authenticated principal with minimum READ_ONLY role. Protected by rate limiting.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from ipo_platform.api.dependencies import get_query_service
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
            except (ValueError, TypeError):
                issue_size_cr = None
        low = getattr(rec.issue_structure.price_band_low, "value", None)
        high = getattr(rec.issue_structure.price_band_high, "value", None)
        if low is not None and high is not None:
            price_band = f"{low} - {high}"

    open_date = rec.ipo_status.open_date if rec.ipo_status else None
    close_date = rec.ipo_status.close_date if rec.ipo_status else None
    listing_date = rec.ipo_status.listing_date if rec.ipo_status else None

    # GMP
    gmp_pct = None
    if rec.gmp_data and hasattr(rec.gmp_data, "gmp_percentage"):
        try:
            gmp_pct = float(rec.gmp_data.gmp_percentage)
        except (ValueError, TypeError):
            gmp_pct = None

    return IPOListItem(
        ipo_id=ipo_id,
        company_name=company_name,
        status=ipo_status_val,
        sector=sector,
        issue_size_cr=issue_size_cr,
        price_band=price_band,
        open_date=open_date,
        close_date=close_date,
        listing_date=listing_date,
        gmp_percentage=gmp_pct,
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
