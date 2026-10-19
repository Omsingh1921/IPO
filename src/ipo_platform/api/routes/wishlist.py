"""
User Wishlist & Post-Listing History REST Endpoints for Indian IPO Platform.
Persists and retrieves user-bookmarked IPO offerings in the database (Table: user_wishlist)
and tracks wishlisted offerings post-listing with actual listing prices and returns (Table: user_wishlist_history).
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from ipo_platform.api.dependencies import get_db, get_query_service
from ipo_platform.api.routes.ipos import _to_list_item
from ipo_platform.api.schemas import (
    WishlistHistoryItemDto,
    WishlistHistoryListResponse,
    UpdateListingPriceRequest,
)
from ipo_platform.db.models import (
    WishlistModel,
    WishlistHistoryModel,
    IPOMasterModel,
    HistoricalPerformanceModel,
    GMPLogModel,
)
from ipo_platform.security.auth import get_current_principal, AuthenticatedPrincipal
from ipo_platform.security.rbac import Role, require_role
from ipo_platform.services.query_service import IPOQueryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


def _resolve_user_id(principal: Optional[AuthenticatedPrincipal]) -> str:
    if principal and getattr(principal, "principal_id", None):
        return principal.principal_id
    return "default_user"


def _to_history_dto(r: WishlistHistoryModel) -> WishlistHistoryItemDto:
    return WishlistHistoryItemDto(
        id=r.id,
        ipo_id=r.ipo_id,
        company_name=r.company_name or r.ipo_id,
        segment=r.segment,
        issue_price=float(r.issue_price) if r.issue_price is not None else None,
        listing_price=float(r.listing_price) if r.listing_price is not None else None,
        listing_gain_pct=float(r.listing_gain_pct) if r.listing_gain_pct is not None else None,
        listing_date=r.listing_date.isoformat() if r.listing_date else None,
        listing_day_close=float(r.listing_day_close) if r.listing_day_close is not None else None,
        status=r.status or "Listed",
        notes=r.notes,
        wishlist_added_at=r.wishlist_added_at.isoformat() if r.wishlist_added_at else None,
        created_at=r.created_at.isoformat() if r.created_at else None,
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
    )


def _sync_wishlist_history_internal(db: Session, user_id: str) -> List[WishlistHistoryModel]:
    """
    Scans user's wishlist offerings. If any offering is listed (or reaches its listing date),
    automatically archives it into user_wishlist_history along with its issue price, actual or
    implied listing price, and calculated listing gain percentage.
    """
    today = date.today()

    wish_items = db.execute(
        select(WishlistModel).where(WishlistModel.user_id == user_id)
    ).scalars().all()

    for w in wish_items:
        ipo = db.execute(
            select(IPOMasterModel).where(IPOMasterModel.ipo_id == w.ipo_id)
        ).scalar_one_or_none()

        if not ipo:
            continue

        is_listed = (
            (ipo.listing_status and ipo.listing_status.strip().lower() == "listed")
            or (ipo.status and ipo.status.strip().lower() in ("closed", "listed"))
            or (ipo.listing_date is not None and ipo.listing_date <= today)
        )

        if not is_listed:
            continue

        hist = db.execute(
            select(WishlistHistoryModel).where(
                WishlistHistoryModel.user_id == user_id,
                WishlistHistoryModel.ipo_id == w.ipo_id,
            )
        ).scalar_one_or_none()

        # Determine Issue Price
        issue_price = None
        if ipo.issue_price is not None:
            issue_price = float(ipo.issue_price)
        elif ipo.price_band_high is not None:
            issue_price = float(ipo.price_band_high)
        elif ipo.price_band_low is not None:
            issue_price = float(ipo.price_band_low)

        # Determine Listing Price & Day Close
        listing_price = float(hist.listing_price) if hist and hist.listing_price is not None else None
        listing_day_close = float(hist.listing_day_close) if hist and hist.listing_day_close is not None else None

        if listing_price is None:
            hp = db.execute(
                select(HistoricalPerformanceModel).where(HistoricalPerformanceModel.ipo_id == w.ipo_id)
            ).scalar_one_or_none()

            if hp and hp.listing_price is not None:
                listing_price = float(hp.listing_price)
                if hp.listing_day_close is not None:
                    listing_day_close = float(hp.listing_day_close)
            else:
                # Check GMP implied price
                gmp = db.execute(
                    select(GMPLogModel)
                    .where(GMPLogModel.ipo_id == w.ipo_id)
                    .order_by(GMPLogModel.gmp_date.desc(), GMPLogModel.gmp_time.desc())
                ).scalars().first()
                if gmp and gmp.implied_price is not None and gmp.implied_price > 0:
                    listing_price = float(gmp.implied_price)

        # Calculate Listing Gain %
        listing_gain_pct = None
        if listing_price is not None and issue_price is not None and issue_price > 0:
            listing_gain_pct = round(((listing_price - issue_price) / issue_price) * 100.0, 2)
        elif hist and hist.listing_gain_pct is not None:
            listing_gain_pct = float(hist.listing_gain_pct)

        if hist:
            # Update missing attributes
            if hist.issue_price is None and issue_price is not None:
                hist.issue_price = issue_price
            if hist.listing_price is None and listing_price is not None:
                hist.listing_price = listing_price
            if listing_gain_pct is not None and hist.listing_gain_pct != listing_gain_pct:
                hist.listing_gain_pct = listing_gain_pct
            if hist.listing_date is None and ipo.listing_date is not None:
                hist.listing_date = ipo.listing_date
            if hist.listing_day_close is None and listing_day_close is not None:
                hist.listing_day_close = listing_day_close
            if hist.company_name is None:
                hist.company_name = ipo.company_name
            if hist.segment is None:
                hist.segment = ipo.segment
            if hist.wishlist_added_at is None and w.created_at is not None:
                hist.wishlist_added_at = w.created_at
        else:
            new_hist = WishlistHistoryModel(
                user_id=user_id,
                ipo_id=w.ipo_id,
                company_name=w.company_name or ipo.company_name,
                segment=ipo.segment,
                issue_price=issue_price,
                listing_price=listing_price,
                listing_gain_pct=listing_gain_pct,
                listing_date=ipo.listing_date,
                listing_day_close=listing_day_close,
                status="Listed",
                wishlist_added_at=w.created_at,
            )
            db.add(new_hist)

    db.commit()

    stmt = (
        select(WishlistHistoryModel)
        .where(WishlistHistoryModel.user_id == user_id)
        .order_by(WishlistHistoryModel.listing_date.desc(), WishlistHistoryModel.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


# ==============================================================================
# Fast ID Lookup
# ==============================================================================

@router.get(
    "/ids",
    summary="Get Wishlisted IPO IDs",
    description="Returns array of wishlisted ipo_ids for fast client-side state synchronization.",
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def get_wishlist_ids(
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> Dict[str, List[str]]:
    """Returns list of ipo_ids saved in the user's database wishlist."""
    user_id = _resolve_user_id(principal)
    stmt = select(WishlistModel.ipo_id).where(WishlistModel.user_id == user_id)
    ids = db.execute(stmt).scalars().all()
    return {"wishlist": list(ids)}


# ==============================================================================
# Post-Listing History Endpoints
# ==============================================================================

@router.get(
    "/history",
    summary="Get Wishlist Post-Listing History",
    description="Retrieves post-listing performance history for wishlisted offerings with actual listing prices and returns.",
    response_model=WishlistHistoryListResponse,
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def get_wishlist_history(
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> WishlistHistoryListResponse:
    """Returns all wishlisted offerings that have listed, including listing price and return percentage."""
    user_id = _resolve_user_id(principal)
    records = _sync_wishlist_history_internal(db, user_id)
    items = [_to_history_dto(r) for r in records]
    return WishlistHistoryListResponse(total=len(items), items=items)


@router.post(
    "/history/sync",
    summary="Synchronize Wishlist Offerings with Listing Events",
    description="Scans user wishlist for offerings that reached listing status and archives them to history with listing prices.",
    response_model=WishlistHistoryListResponse,
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def sync_wishlist_history(
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> WishlistHistoryListResponse:
    """Explicitly triggers auto-sync between active wishlist items and listing events."""
    user_id = _resolve_user_id(principal)
    records = _sync_wishlist_history_internal(db, user_id)
    items = [_to_history_dto(r) for r in records]
    return WishlistHistoryListResponse(total=len(items), items=items)


@router.post(
    "/history/{ipo_id}",
    summary="Record or Update Listing Price in Wishlist History",
    description="Manually records or updates the actual listing price, day close, or notes for a wishlisted IPO.",
    response_model=WishlistHistoryItemDto,
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def record_listing_price(
    ipo_id: str = Path(..., description="Unique ID of IPO offering"),
    payload: UpdateListingPriceRequest = ...,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> WishlistHistoryItemDto:
    """Persists or updates actual listing price and recalculates listing gain % for an IPO in user's history."""
    user_id = _resolve_user_id(principal)

    hist = db.execute(
        select(WishlistHistoryModel).where(
            WishlistHistoryModel.user_id == user_id,
            WishlistHistoryModel.ipo_id == ipo_id,
        )
    ).scalar_one_or_none()

    ipo = db.execute(
        select(IPOMasterModel).where(IPOMasterModel.ipo_id == ipo_id)
    ).scalar_one_or_none()

    company_name = (ipo.company_name if ipo else None) or (hist.company_name if hist else None) or ipo_id
    segment = (ipo.segment if ipo else None) or (hist.segment if hist else None) or "Mainboard"

    # Resolve issue price
    issue_price = payload.issue_price
    if issue_price is None:
        if hist and hist.issue_price is not None:
            issue_price = float(hist.issue_price)
        elif ipo and ipo.issue_price is not None:
            issue_price = float(ipo.issue_price)
        elif ipo and ipo.price_band_high is not None:
            issue_price = float(ipo.price_band_high)
        elif ipo and ipo.price_band_low is not None:
            issue_price = float(ipo.price_band_low)

    listing_price = payload.listing_price
    listing_gain_pct = None
    if listing_price is not None and issue_price is not None and issue_price > 0:
        listing_gain_pct = round(((listing_price - issue_price) / issue_price) * 100.0, 2)

    listing_date = None
    if payload.listing_date:
        try:
            listing_date = date.fromisoformat(payload.listing_date)
        except Exception:
            pass
    elif ipo and ipo.listing_date:
        listing_date = ipo.listing_date
    elif hist and hist.listing_date:
        listing_date = hist.listing_date
    else:
        listing_date = date.today()

    listing_day_close = payload.listing_day_close
    notes = payload.notes

    if hist:
        hist.listing_price = listing_price
        if issue_price is not None:
            hist.issue_price = issue_price
        if listing_gain_pct is not None:
            hist.listing_gain_pct = listing_gain_pct
        if listing_day_close is not None:
            hist.listing_day_close = listing_day_close
        if listing_date is not None:
            hist.listing_date = listing_date
        if notes is not None:
            hist.notes = notes
        hist.status = "Listed"
    else:
        w = db.execute(
            select(WishlistModel).where(WishlistModel.user_id == user_id, WishlistModel.ipo_id == ipo_id)
        ).scalar_one_or_none()

        hist = WishlistHistoryModel(
            user_id=user_id,
            ipo_id=ipo_id,
            company_name=company_name,
            segment=segment,
            issue_price=issue_price,
            listing_price=listing_price,
            listing_gain_pct=listing_gain_pct,
            listing_date=listing_date,
            listing_day_close=listing_day_close,
            status="Listed",
            notes=notes,
            wishlist_added_at=w.created_at if w else None,
        )
        db.add(hist)

    # Update or insert into HistoricalPerformanceModel for system-wide metrics
    hp = db.execute(
        select(HistoricalPerformanceModel).where(HistoricalPerformanceModel.ipo_id == ipo_id)
    ).scalar_one_or_none()

    if hp:
        hp.listing_price = listing_price
        if listing_day_close:
            hp.listing_day_close = listing_day_close
        if listing_gain_pct is not None:
            hp.listing_day_return = listing_gain_pct
    else:
        year = listing_date.year if listing_date else date.today().year
        new_hp = HistoricalPerformanceModel(
            ipo_id=ipo_id,
            ipo_year=year,
            listing_price=listing_price,
            listing_day_close=listing_day_close or listing_price,
            listing_day_return=listing_gain_pct or 0.0,
            source_id=None,
        )
        db.add(new_hp)

    db.commit()
    db.refresh(hist)
    return _to_history_dto(hist)


@router.delete(
    "/history/{ipo_id}",
    summary="Remove Entry from Wishlist Post-Listing History",
    description="Deletes a specific record from user's post-listing history table.",
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def remove_from_wishlist_history(
    ipo_id: str = Path(..., description="Unique ID of IPO to remove from history"),
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> Dict[str, Any]:
    """Deletes offering from user_wishlist_history table."""
    user_id = _resolve_user_id(principal)
    stmt = delete(WishlistHistoryModel).where(
        WishlistHistoryModel.user_id == user_id,
        WishlistHistoryModel.ipo_id == ipo_id,
    )
    res = db.execute(stmt)
    db.commit()

    return {
        "status": "removed",
        "ipo_id": ipo_id,
        "deleted_count": res.rowcount,
        "message": f"Removed {ipo_id} from post-listing history",
    }


# ==============================================================================
# Active Wishlist Endpoints
# ==============================================================================

@router.get(
    "",
    summary="List Wishlisted IPO Offerings",
    description="Retrieves full details for all offerings saved in the database wishlist.",
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def get_wishlist(
    db: Session = Depends(get_db),
    query_service: IPOQueryService = Depends(get_query_service),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> Dict[str, Any]:
    """Retrieves full offering data for all items in user's database wishlist."""
    user_id = _resolve_user_id(principal)
    stmt = select(WishlistModel).where(WishlistModel.user_id == user_id).order_by(WishlistModel.created_at.desc())
    records = db.execute(stmt).scalars().all()

    items = []
    for r in records:
        try:
            full_rec = query_service.get_ipo_details(r.ipo_id)
            if full_rec:
                item_dict = _to_list_item(full_rec).model_dump()
                item_dict["wishlist_added_at"] = r.created_at.isoformat() if r.created_at else None
                items.append(item_dict)
            else:
                items.append({
                    "ipo_id": r.ipo_id,
                    "company_name": r.company_name or r.ipo_id,
                    "status": "Active",
                    "wishlist_added_at": r.created_at.isoformat() if r.created_at else None,
                })
        except Exception as e:
            logger.warning("Error loading wishlist IPO %s: %s", r.ipo_id, e)
            items.append({
                "ipo_id": r.ipo_id,
                "company_name": r.company_name or r.ipo_id,
                "status": "Active",
            })

    return {
        "total": len(items),
        "items": items,
    }


@router.post(
    "/{ipo_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add IPO to Database Wishlist",
    description="Persists an offering into user's database wishlist table and automatically syncs post-listing history if already listed.",
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def add_to_wishlist(
    ipo_id: str = Path(..., description="Unique ID of offering to bookmark"),
    db: Session = Depends(get_db),
    query_service: IPOQueryService = Depends(get_query_service),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> Dict[str, Any]:
    """Adds offering to database user_wishlist and syncs to history if already listed."""
    user_id = _resolve_user_id(principal)

    existing = db.execute(
        select(WishlistModel).where(WishlistModel.user_id == user_id, WishlistModel.ipo_id == ipo_id)
    ).scalar_one_or_none()

    if existing:
        return {"status": "exists", "ipo_id": ipo_id, "message": "Already present in database wishlist"}

    company_name = ipo_id
    try:
        rec = query_service.get_ipo_details(ipo_id)
        if rec and rec.ipo_entity and rec.ipo_entity.company_name:
            company_name = rec.ipo_entity.company_name
        else:
            ipo_m = db.execute(select(IPOMasterModel).where(IPOMasterModel.ipo_id == ipo_id)).scalar_one_or_none()
            if ipo_m and ipo_m.company_name:
                company_name = ipo_m.company_name
    except Exception:
        pass

    new_item = WishlistModel(
        user_id=user_id,
        ipo_id=ipo_id,
        company_name=company_name,
    )
    db.add(new_item)
    db.commit()

    # Automatically check if this newly wishlisted IPO has already listed
    _sync_wishlist_history_internal(db, user_id)

    return {
        "status": "added",
        "ipo_id": ipo_id,
        "company_name": company_name,
        "message": f"Successfully saved {company_name} to database wishlist",
    }


@router.delete(
    "/{ipo_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove IPO from Database Wishlist",
    description="Deletes an offering from user's database wishlist table.",
    dependencies=[Depends(require_role(Role.READ_ONLY))],
)
def remove_from_wishlist(
    ipo_id: str = Path(..., description="Unique ID of offering to remove from wishlist"),
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_role(Role.READ_ONLY)),
) -> Dict[str, Any]:
    """Deletes offering from user_wishlist table."""
    user_id = _resolve_user_id(principal)

    stmt = delete(WishlistModel).where(WishlistModel.user_id == user_id, WishlistModel.ipo_id == ipo_id)
    res = db.execute(stmt)
    db.commit()

    return {
        "status": "removed",
        "ipo_id": ipo_id,
        "deleted_count": res.rowcount,
        "message": f"Removed {ipo_id} from database wishlist",
    }
