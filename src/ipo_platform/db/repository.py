"""
Repository Persistence Layer for Indian IPO Platform.
Implements segregated repository pattern for reads, writes, GMP tracking, and backtesting.
Enforces Optimistic Concurrency Control (version_id) and atomic transaction boundaries.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from ipo_platform.db.exceptions import (
    ConstraintViolationError,
    DataIntegrityError,
    DuplicateIPOSlugError,
    OptimisticLockError,
)
from ipo_platform.db.mappers import MasterIPOMapper
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
from ipo_platform.models.enums import IPOStatusEnum, SourceTypeEnum
from ipo_platform.models.schema import (
    GMPData,
    HistoricalIPO,
    MasterIPORecord,
    PerformanceEvent,
)

# -----------------------------------------------------------------------------
# Internal Child Record Loader Helper
# -----------------------------------------------------------------------------


def _fetch_related_models(session: Session, ipo_id: str) -> Dict[str, Any]:
    """Internal helper to retrieve all associated child ORM models for an IPO."""
    sources = session.execute(
        select(SourceModel).where(SourceModel.source_id.like(f"SRC_{ipo_id}_%"))
    ).scalars().all()

    objects = session.execute(
        select(ObjectOfIssueModel).where(ObjectOfIssueModel.ipo_id == ipo_id)
    ).scalars().all()

    financials = session.execute(
        select(FinancialModel).where(FinancialModel.ipo_id == ipo_id)
    ).scalars().all()

    valuation = session.execute(
        select(ValuationModel).where(ValuationModel.ipo_id == ipo_id)
    ).scalars().first()

    subscriptions = session.execute(
        select(SubscriptionModel)
        .where(SubscriptionModel.ipo_id == ipo_id)
        .order_by(SubscriptionModel.subscription_date.desc(), SubscriptionModel.id.desc())
    ).scalars().all()

    anchor_header = session.execute(
        select(AnchorHeaderModel).where(AnchorHeaderModel.ipo_id == ipo_id)
    ).scalars().first()

    anchor_investors: List[AnchorInvestorModel] = []
    if anchor_header:
        anchor_investors = list(session.execute(
            select(AnchorInvestorModel).where(AnchorInvestorModel.anchor_id == anchor_header.anchor_id)
        ).scalars().all())

    gmp_logs = session.execute(
        select(GMPLogModel)
        .where(GMPLogModel.ipo_id == ipo_id)
        .order_by(GMPLogModel.gmp_date.desc(), GMPLogModel.gmp_time.desc())
    ).scalars().all()

    peers = session.execute(
        select(PeerCompanyModel).where(PeerCompanyModel.ipo_id == ipo_id)
    ).scalars().all()

    risks = session.execute(
        select(RiskDisclosureModel).where(RiskDisclosureModel.ipo_id == ipo_id)
    ).scalars().all()

    scenario = session.execute(
        select(ScenarioModel).where(ScenarioModel.ipo_id == ipo_id)
    ).scalars().first()

    historical_perf = session.execute(
        select(HistoricalPerformanceModel).where(HistoricalPerformanceModel.ipo_id == ipo_id)
    ).scalars().first()

    performance_events = session.execute(
        select(PerformanceEventModel)
        .where(PerformanceEventModel.ipo_id == ipo_id)
        .order_by(PerformanceEventModel.days_from_listing.asc())
    ).scalars().all()

    return {
        "sources": list(sources),
        "objects_of_issue": list(objects),
        "financials": list(financials),
        "valuation": valuation,
        "subscriptions": list(subscriptions),
        "anchor_header": anchor_header,
        "anchor_investors": list(anchor_investors),
        "gmp_logs": list(gmp_logs),
        "peers": list(peers),
        "risks": list(risks),
        "scenario": scenario,
        "historical_performance": historical_perf,
        "performance_events": list(performance_events),
    }


# -----------------------------------------------------------------------------
# 1. Read Repository
# -----------------------------------------------------------------------------


class IPOReadRepository:
    """Read-only query repository for IPO domain aggregates."""

    @staticmethod
    def get_by_id(session: Session, ipo_id: str) -> Optional[MasterIPORecord]:
        """Retrieves active MasterIPORecord by unique ipo_id."""
        stmt = select(IPOMasterModel).where(
            IPOMasterModel.ipo_id == ipo_id,
            IPOMasterModel.is_active == True,
        )
        master = session.execute(stmt).scalars().first()
        if not master:
            return None

        related = _fetch_related_models(session, ipo_id)
        return MasterIPOMapper.models_to_record(master, related)

    @staticmethod
    def get_by_slug(session: Session, slug: str) -> Optional[MasterIPORecord]:
        """Retrieves MasterIPORecord by ipo_id slug or ticker symbol."""
        stmt = select(IPOMasterModel).where(
            (IPOMasterModel.ipo_id == slug) | (IPOMasterModel.ticker_symbol == slug),
            IPOMasterModel.is_active == True,
        )
        master = session.execute(stmt).scalars().first()
        if not master:
            return None

        related = _fetch_related_models(session, master.ipo_id)
        return MasterIPOMapper.models_to_record(master, related)

    @staticmethod
    def list_all(session: Session, skip: int = 0, limit: int = 100) -> List[MasterIPORecord]:
        """Lists active MasterIPORecords with pagination."""
        stmt = (
            select(IPOMasterModel)
            .where(IPOMasterModel.is_active == True)
            .order_by(IPOMasterModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        masters = session.execute(stmt).scalars().all()
        results: List[MasterIPORecord] = []
        for master in masters:
            related = _fetch_related_models(session, master.ipo_id)
            results.append(MasterIPOMapper.models_to_record(master, related))
        return results

    @staticmethod
    def list_by_status(
        session: Session,
        status: Union[IPOStatusEnum, str],
        skip: int = 0,
        limit: int = 100,
    ) -> List[MasterIPORecord]:
        """Lists active MasterIPORecords filtered by offering status."""
        status_val = status.value if isinstance(status, IPOStatusEnum) else str(status)
        stmt = (
            select(IPOMasterModel)
            .where(
                IPOMasterModel.status == status_val,
                IPOMasterModel.is_active == True,
            )
            .order_by(IPOMasterModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        masters = session.execute(stmt).scalars().all()
        results: List[MasterIPORecord] = []
        for master in masters:
            related = _fetch_related_models(session, master.ipo_id)
            results.append(MasterIPOMapper.models_to_record(master, related))
        return results


# -----------------------------------------------------------------------------
# 2. Write Repository
# -----------------------------------------------------------------------------


def _normalize_name_for_dedup(name: str) -> str:
    """
    Normalizes company names for deduplication across exchanges.
    Removes corporate legal suffixes, punctuation, and whitespace.
    """
    if not name:
        return ""
    clean = name.lower()
    clean = re.sub(r"[^\w\s]", " ", clean)
    stop_words = {
        "limited", "ltd", "pvt", "private", "inc", "corp", "corporation",
        "llp", "company", "co", "india", "technologies", "technology",
        "services", "service", "manufacturing", "businesses", "business",
        "transmissions", "transmission", "investments", "investment",
        "solutions", "solution", "holdings", "holding", "enterprises", "enterprise",
    }
    tokens = [w for w in clean.split() if w not in stop_words and len(w) > 1]
    if not tokens:
        tokens = [w for w in clean.split() if len(w) > 1]
    return "".join(tokens)


class IPOWriteRepository:
    """Transactional write repository supporting OCC versioning and soft deletion."""

    @staticmethod
    def save_master_record(session: Session, record: MasterIPORecord) -> MasterIPORecord:
        """
        Atomically persists or updates a MasterIPORecord aggregate.
        Enforces strict multi-layer deduplication (ID, ISIN, Ticker, and Normalized Company Name)
        to prevent duplicate company entries across NSE, BSE, and upstream feeds.

        Raises:
            DuplicateIPOSlugError: If ipo_id or unique ISIN already exists on insert.
            OptimisticLockError: If version collision occurs on update.
            DataIntegrityError: If mapping or constraint fails.
        """
        ipo_id = record.ipo_entity.ipo_id
        company_name = record.ipo_entity.company_name or ""
        ticker_symbol = record.ipo_entity.ticker_symbol or ""
        isin = record.ipo_entity.isin or ""
        models_dict = MasterIPOMapper.record_to_models(record)

        try:
            # Multi-layer deduplication matching:
            # 1. Exact match by ipo_id
            existing_master = session.execute(
                select(IPOMasterModel).where(IPOMasterModel.ipo_id == ipo_id)
            ).scalars().first()

            # 2. Match by ISIN if genuine (12 chars, not dummy INEBSE/placeholder)
            if not existing_master and isin and len(isin) == 12 and not isin.startswith("INEBSE"):
                existing_master = session.execute(
                    select(IPOMasterModel).where(
                        IPOMasterModel.isin == isin,
                        IPOMasterModel.is_active == True,
                    )
                ).scalars().first()

            # 3. Match by non-numeric ticker symbol
            if not existing_master and ticker_symbol and not ticker_symbol.isdigit() and ticker_symbol not in ("BSE_OFFERING", "NSE_OFFERING"):
                existing_master = session.execute(
                    select(IPOMasterModel).where(
                        IPOMasterModel.ticker_symbol == ticker_symbol,
                        IPOMasterModel.is_active == True,
                    )
                ).scalars().first()

            # 4. Match by normalized company name across active offerings
            if not existing_master:
                target_norm = _normalize_name_for_dedup(company_name)
                if target_norm and len(target_norm) >= 4:
                    active_masters = session.execute(
                        select(IPOMasterModel).where(IPOMasterModel.is_active == True)
                    ).scalars().all()
                    for cand in active_masters:
                        cand_norm = _normalize_name_for_dedup(cand.company_name)
                        if not cand_norm:
                            continue
                        if target_norm == cand_norm:
                            existing_master = cand
                            break
                        if len(target_norm) >= 5 and len(cand_norm) >= 5:
                            if target_norm in cand_norm or cand_norm in target_norm:
                                existing_master = cand
                                break

            if existing_master:
                is_same_id = (existing_master.ipo_id == ipo_id)
                is_exchange_variant = (
                    (ipo_id.startswith("BSE-") and (existing_master.ipo_id.startswith("NSE-") or existing_master.ipo_id.startswith("TEST-")))
                    or (ipo_id.startswith("NSE-") and (existing_master.ipo_id.startswith("BSE-") or existing_master.ipo_id.startswith("TEST-")))
                )

                if not is_same_id and not is_exchange_variant:
                    raise DuplicateIPOSlugError(
                        f"Duplicate IPO record detected: offering '{company_name}' (ISIN: {isin}) "
                        f"already exists as '{existing_master.ipo_id}'."
                    )

                # Update existing master fields in-place without duplicating records
                new_master: IPOMasterModel = models_dict["master"]
                target_ipo_id = existing_master.ipo_id

                if not existing_master.company_name or len(new_master.company_name) > len(existing_master.company_name):
                    existing_master.company_name = new_master.company_name
                if new_master.company_legal_name:
                    existing_master.company_legal_name = new_master.company_legal_name

                # Preserve clean alphabetic ticker_symbol
                if new_master.ticker_symbol and not new_master.ticker_symbol.isdigit():
                    existing_master.ticker_symbol = new_master.ticker_symbol

                # Update genuine ISIN
                if new_master.isin and not new_master.isin.startswith("INEBSE"):
                    existing_master.isin = new_master.isin

                if new_master.segment:
                    existing_master.segment = new_master.segment
                if new_master.sector:
                    existing_master.sector = new_master.sector
                if new_master.industry:
                    existing_master.industry = new_master.industry
                existing_master.status = new_master.status
                existing_master.research_date = new_master.research_date
                existing_master.research_time = new_master.research_time
                existing_master.data_cutoff = new_master.data_cutoff
                existing_master.open_date = new_master.open_date
                existing_master.close_date = new_master.close_date
                if hasattr(new_master, "allotment_date") and new_master.allotment_date:
                    existing_master.allotment_date = new_master.allotment_date
                if new_master.listing_date:
                    existing_master.listing_date = new_master.listing_date
                existing_master.listing_status = new_master.listing_status
                if new_master.issue_size and float(new_master.issue_size) > 0:
                    existing_master.issue_size = new_master.issue_size
                if new_master.fresh_issue_amount:
                    existing_master.fresh_issue_amount = new_master.fresh_issue_amount
                if new_master.ofs_amount:
                    existing_master.ofs_amount = new_master.ofs_amount
                if new_master.fresh_issue_percentage:
                    existing_master.fresh_issue_percentage = new_master.fresh_issue_percentage
                if new_master.ofs_percentage:
                    existing_master.ofs_percentage = new_master.ofs_percentage
                if new_master.face_value:
                    existing_master.face_value = new_master.face_value
                if new_master.price_band_high and float(new_master.price_band_high) > 0:
                    existing_master.price_band_low = new_master.price_band_low
                    existing_master.price_band_high = new_master.price_band_high
                    existing_master.issue_price = new_master.issue_price
                if new_master.lot_size and int(new_master.lot_size) > 0:
                    existing_master.lot_size = new_master.lot_size
                    existing_master.minimum_investment = new_master.minimum_investment
                if new_master.employee_reservation:
                    existing_master.employee_reservation = new_master.employee_reservation
                if new_master.shareholder_reservation:
                    existing_master.shareholder_reservation = new_master.shareholder_reservation
                if new_master.other_reservation:
                    existing_master.other_reservation = new_master.other_reservation

                session.flush()
            else:
                # Insert new master and sources
                session.add(models_dict["master"])
                for src in models_dict.get("sources", []):
                    session.add(src)
                session.flush()

                # Add child records
                for obj in models_dict.get("objects_of_issue", []):
                    session.add(obj)
                for fin in models_dict.get("financials", []):
                    session.add(fin)
                if models_dict.get("valuation"):
                    session.add(models_dict["valuation"])
                for sub in models_dict.get("subscriptions", []):
                    session.add(sub)
                if models_dict.get("anchor_header"):
                    session.add(models_dict["anchor_header"])
                for inv in models_dict.get("anchor_investors", []):
                    session.add(inv)
                for gmp in models_dict.get("gmp_logs", []):
                    session.add(gmp)
                for peer in models_dict.get("peers", []):
                    session.add(peer)
                for risk in models_dict.get("risks", []):
                    session.add(risk)
                if models_dict.get("scenario"):
                    session.add(models_dict["scenario"])
                if models_dict.get("historical_performance"):
                    session.add(models_dict["historical_performance"])
                for pe in models_dict.get("performance_events", []):
                    session.add(pe)

                session.flush()
            final_ipo_id = existing_master.ipo_id if existing_master else ipo_id
            return IPOReadRepository.get_by_id(session, final_ipo_id) or record

        except StaleDataError as err:
            raise OptimisticLockError(f"Optimistic lock collision for IPO '{ipo_id}': {err}") from err
        except IntegrityError as err:
            if "duplicate" in str(err).lower() or "unique" in str(err).lower():
                raise DuplicateIPOSlugError(f"Duplicate IPO record or unique constraint violation for '{ipo_id}': {err}") from err
            raise ConstraintViolationError(f"Foreign key or constraint violation for '{ipo_id}': {err}") from err
        except SQLAlchemyError as err:
            raise DataIntegrityError(f"Failed to save IPO master record '{ipo_id}': {err}") from err

    @staticmethod
    def update_status(
        session: Session,
        ipo_id: str,
        new_status: Union[IPOStatusEnum, str],
        expected_version: Optional[int] = None,
    ) -> bool:
        """
        Updates offering lifecycle status with optional OCC version check.

        Raises:
            OptimisticLockError: If expected_version does not match current version_id.
        """
        master = session.execute(
            select(IPOMasterModel).where(
                IPOMasterModel.ipo_id == ipo_id,
                IPOMasterModel.is_active == True,
            )
        ).scalars().first()

        if not master:
            return False

        if expected_version is not None and master.version_id != expected_version:
            raise OptimisticLockError(
                f"Version mismatch for IPO '{ipo_id}'. Expected {expected_version}, found {master.version_id}."
            )

        status_val = new_status.value if isinstance(new_status, IPOStatusEnum) else str(new_status)
        master.status = status_val
        session.flush()
        return True

    @staticmethod
    def soft_delete(
        session: Session,
        ipo_id: str,
        expected_version: Optional[int] = None,
    ) -> bool:
        """
        Soft deletes an IPO record by setting is_active=False and deleted_at timestamp.

        Raises:
            OptimisticLockError: If expected_version does not match current version_id.
        """
        master = session.execute(
            select(IPOMasterModel).where(
                IPOMasterModel.ipo_id == ipo_id,
                IPOMasterModel.is_active == True,
            )
        ).scalars().first()

        if not master:
            return False

        if expected_version is not None and master.version_id != expected_version:
            raise OptimisticLockError(
                f"Version mismatch for IPO '{ipo_id}'. Expected {expected_version}, found {master.version_id}."
            )

        master.is_active = False
        master.deleted_at = datetime.now()
        session.flush()
        return True

    @staticmethod
    def update_dates(
        session: Session,
        ipo_id: str,
        allotment_date: Optional[str] = None,
        listing_date: Optional[str] = None,
    ) -> bool:
        """
        Updates allotment_date and/or listing_date for an active IPO offering.
        """
        master = session.execute(
            select(IPOMasterModel).where(
                IPOMasterModel.ipo_id == ipo_id,
                IPOMasterModel.is_active == True,
            )
        ).scalars().first()
        if not master:
            return False

        updated = False
        if allotment_date:
            try:
                clean_ad = str(allotment_date).split("T")[0].strip()
                if len(clean_ad) == 10 and clean_ad[4] == "-" and clean_ad[7] == "-":
                    master.allotment_date = datetime.strptime(clean_ad, "%Y-%m-%d").date()
                    updated = True
            except Exception:
                pass
        if listing_date:
            try:
                clean_ld = str(listing_date).split("T")[0].strip()
                if len(clean_ld) == 10 and clean_ld[4] == "-" and clean_ld[7] == "-":
                    master.listing_date = datetime.strptime(clean_ld, "%Y-%m-%d").date()
                    updated = True
            except Exception:
                pass

        if updated:
            session.flush()
        return updated



# -----------------------------------------------------------------------------
# 3. GMP Repository
# -----------------------------------------------------------------------------


class GMPRepository:
    """Time-series indicative Grey Market Premium repository."""

    @staticmethod
    def save_gmp_snapshot(session: Session, ipo_id: str, gmp_data: GMPData) -> GMPLogModel:
        """Persists a new GMP quote snapshot or updates existing quote for today."""
        stype = gmp_data.source_type.value if isinstance(gmp_data.source_type, SourceTypeEnum) else str(gmp_data.source_type)
        today_val = datetime.now().date()
        existing = session.execute(
            select(GMPLogModel).where(
                (GMPLogModel.ipo_id == ipo_id) & (GMPLogModel.gmp_date == today_val)
            ).order_by(GMPLogModel.gmp_time.desc())
        ).scalars().first()
        if existing:
            existing.gmp_value = gmp_data.gmp_value
            existing.gmp_percentage = gmp_data.gmp_percentage
            existing.reference_price = gmp_data.reference_price
            existing.implied_price = gmp_data.implied_price
            existing.source_type = stype
            existing.retrieval_timestamp = datetime.now()
            session.flush()
            return existing

        gmp_model = GMPLogModel(
            ipo_id=ipo_id,
            gmp_date=today_val,
            gmp_time=datetime.now().time(),
            gmp_value=gmp_data.gmp_value,
            gmp_percentage=gmp_data.gmp_percentage,
            reference_price=gmp_data.reference_price,
            implied_price=gmp_data.implied_price,
            source_type=stype,
            retrieval_timestamp=datetime.now(),
        )
        session.add(gmp_model)
        session.flush()
        return gmp_model

    @staticmethod
    def get_latest_gmp(session: Session, ipo_id: str) -> Optional[GMPData]:
        """Retrieves the latest GMP quote snapshot for an IPO."""
        stmt = (
            select(GMPLogModel)
            .where(GMPLogModel.ipo_id == ipo_id)
            .order_by(GMPLogModel.gmp_date.desc(), GMPLogModel.gmp_time.desc())
        )
        gmp_m = session.execute(stmt).scalars().first()
        if not gmp_m:
            return None

        stype = SourceTypeEnum(gmp_m.source_type) if gmp_m.source_type in SourceTypeEnum._value2member_map_ else SourceTypeEnum.UNOFFICIAL_GMP
        return GMPData(
            gmp_value=gmp_m.gmp_value,
            gmp_percentage=gmp_m.gmp_percentage or 0.0,
            gmp_date=gmp_m.gmp_date.isoformat(),
            gmp_time=gmp_m.gmp_time.isoformat(),
            reference_price=gmp_m.reference_price,
            implied_price=gmp_m.implied_price,
            source="Market Tracker",
            source_type=stype,
        )


# -----------------------------------------------------------------------------
# 4. Backtest Repository
# -----------------------------------------------------------------------------


class BacktestRepository:
    """Historical post-listing outcomes and longitudinal performance event stream repository."""

    @staticmethod
    def save_historical_performance(
        session: Session,
        ipo_id: str,
        hist_data: HistoricalIPO,
    ) -> HistoricalPerformanceModel:
        """Persists historical performance outcomes for post-listing analysis."""
        existing = session.execute(
            select(HistoricalPerformanceModel).where(HistoricalPerformanceModel.ipo_id == ipo_id)
        ).scalars().first()

        def to_flt(val: Any) -> Optional[float]:
            if val is None or val == "Not available":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        if existing:
            existing.ipo_year = hist_data.ipo_year or datetime.now().year
            existing.listing_price = to_flt(hist_data.listing_price) or 0.0
            existing.listing_day_close = to_flt(hist_data.listing_day_close) or 0.0
            existing.listing_day_high = to_flt(hist_data.listing_day_high)
            existing.listing_day_low = to_flt(hist_data.listing_day_low)
            existing.listing_day_return = to_flt(hist_data.listing_day_return) or 0.0
            existing.post_listing_7d_return = to_flt(hist_data.post_listing_7d_return)
            existing.post_listing_30d_return = to_flt(hist_data.post_listing_30d_return)
            existing.post_listing_90d_return = to_flt(hist_data.post_listing_90d_return)
            existing.post_listing_180d_return = to_flt(hist_data.post_listing_180d_return)
            existing.post_listing_1y_return = to_flt(hist_data.post_listing_1y_return)
            existing.max_upside_from_issue_price = to_flt(hist_data.max_upside_from_issue_price)
            existing.max_drawdown_from_issue_price = to_flt(hist_data.max_drawdown_from_issue_price)
            session.flush()
            return existing
        else:
            model = HistoricalPerformanceModel(
                ipo_id=ipo_id,
                ipo_year=hist_data.ipo_year or datetime.now().year,
                listing_price=to_flt(hist_data.listing_price) or 0.0,
                listing_day_close=to_flt(hist_data.listing_day_close) or 0.0,
                listing_day_high=to_flt(hist_data.listing_day_high),
                listing_day_low=to_flt(hist_data.listing_day_low),
                listing_day_return=to_flt(hist_data.listing_day_return) or 0.0,
                post_listing_7d_return=to_flt(hist_data.post_listing_7d_return),
                post_listing_30d_return=to_flt(hist_data.post_listing_30d_return),
                post_listing_90d_return=to_flt(hist_data.post_listing_90d_return),
                post_listing_180d_return=to_flt(hist_data.post_listing_180d_return),
                post_listing_1y_return=to_flt(hist_data.post_listing_1y_return),
                max_upside_from_issue_price=to_flt(hist_data.max_upside_from_issue_price),
                max_drawdown_from_issue_price=to_flt(hist_data.max_drawdown_from_issue_price),
            )
            session.add(model)
            session.flush()
            return model

    @staticmethod
    def get_historical_performance(session: Session, ipo_id: str) -> Optional[HistoricalIPO]:
        """Retrieves HistoricalIPO outcomes for an IPO."""
        hist_m = session.execute(
            select(HistoricalPerformanceModel).where(HistoricalPerformanceModel.ipo_id == ipo_id)
        ).scalars().first()

        if not hist_m:
            return None

        def flt_opt(val: Any) -> Any:
            if val is None:
                return "Not available"
            try:
                return float(val)
            except (ValueError, TypeError):
                return val

        return HistoricalIPO(
            historical_ipo=True,
            ipo_year=hist_m.ipo_year,
            listing_price=flt_opt(hist_m.listing_price),
            listing_day_close=flt_opt(hist_m.listing_day_close),
            listing_day_high=flt_opt(hist_m.listing_day_high),
            listing_day_low=flt_opt(hist_m.listing_day_low),
            listing_day_return=flt_opt(hist_m.listing_day_return),
            post_listing_7d_return=flt_opt(hist_m.post_listing_7d_return),
            post_listing_30d_return=flt_opt(hist_m.post_listing_30d_return),
            post_listing_90d_return=flt_opt(hist_m.post_listing_90d_return),
            post_listing_180d_return=flt_opt(hist_m.post_listing_180d_return),
            post_listing_1y_return=flt_opt(hist_m.post_listing_1y_return),
            max_upside_from_issue_price=flt_opt(hist_m.max_upside_from_issue_price),
            max_drawdown_from_issue_price=flt_opt(hist_m.max_drawdown_from_issue_price),
        )

    @staticmethod
    def save_performance_event(
        session: Session,
        ipo_id: str,
        event: PerformanceEvent,
    ) -> PerformanceEventModel:
        """Persists a longitudinal performance event stream entry."""
        ev_date = datetime.strptime(event.event_date, "%Y-%m-%d").date() if isinstance(event.event_date, str) else event.event_date
        etype = event.event_type.value if getattr(event.event_type, "value", None) else str(event.event_type)

        model = PerformanceEventModel(
            ipo_id=ipo_id,
            event_date=ev_date,
            event_type=etype,
            reference_price=event.reference_price,
            market_price=event.market_price,
            return_percentage=event.return_percentage,
            days_from_listing=event.days_from_listing,
            reached_40_percent_target=event.reached_40_percent_target,
        )
        session.add(model)
        session.flush()
        return model

    @staticmethod
    def list_performance_events(session: Session, ipo_id: str) -> List[PerformanceEvent]:
        """Lists longitudinal performance events for an IPO ordered by days_from_listing."""
        events = session.execute(
            select(PerformanceEventModel)
            .where(PerformanceEventModel.ipo_id == ipo_id)
            .order_by(PerformanceEventModel.days_from_listing.asc())
        ).scalars().all()

        results: List[PerformanceEvent] = []
        for pe in events:
            results.append(
                PerformanceEvent(
                    event_date=pe.event_date.isoformat(),
                    event_type=pe.event_type,
                    reference_price=float(pe.reference_price),
                    market_price=float(pe.market_price),
                    return_percentage=float(pe.return_percentage),
                    days_from_listing=pe.days_from_listing,
                    reached_40_percent_target=pe.reached_40_percent_target,
                    source="Exchange Data",
                )
            )
        return results
