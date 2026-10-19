"""
Application Ingestion Service for Indian IPO Platform.
Acts as a facade encapsulating JSON parsing, file reading, and write repository persistence.
"""

import json
from typing import Any, Dict, Optional

from sqlalchemy import Engine

from ipo_platform.db.repository import GMPRepository, IPOWriteRepository
from ipo_platform.db.session import get_db_session
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.schema import GMPData, MasterIPORecord


class IPOIngestionService:
    """Application Service facade managing data ingestion workflows."""

    def __init__(
        self,
        engine: Engine,
        write_repo: type[IPOWriteRepository] = IPOWriteRepository,
        gmp_repo: type[GMPRepository] = GMPRepository,
    ) -> None:
        """
        Initializes IPOIngestionService with dependency injection.

        Args:
            engine: SQLAlchemy Engine instance.
            write_repo: IPOWriteRepository class or instance.
            gmp_repo: GMPRepository class or instance.
        """
        self.engine = engine
        self.write_repo = write_repo
        self.gmp_repo = gmp_repo

    def ingest_json_dict(self, json_data: Dict[str, Any]) -> MasterIPORecord:
        """
        Parses a raw JSON dictionary into a MasterIPORecord and persists it to the database.

        Args:
            json_data: Raw JSON dictionary payload matching schema version 1.0.

        Returns:
            Persisted MasterIPORecord aggregate.
        """
        record = JSONIngestor.from_dict(json_data)
        return self.ingest_master_record(record)

    def ingest_master_record(self, record: MasterIPORecord) -> MasterIPORecord:
        """
        Directly persists an in-memory MasterIPORecord aggregate to the database.

        Args:
            record: MasterIPORecord aggregate instance.

        Returns:
            Persisted MasterIPORecord aggregate.
        """
        with get_db_session(self.engine) as session:
            saved_record = self.write_repo.save_master_record(session, record)
            return saved_record

    def ingest_json_file(self, file_path: str) -> MasterIPORecord:
        """
        Reads a JSON file from disk, parses, and persists it to the database.

        Args:
            file_path: File system path to JSON research report.

        Returns:
            Persisted MasterIPORecord aggregate.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        return self.ingest_json_dict(json_data)

    def record_gmp_quote(self, ipo_id: str, gmp_data: GMPData) -> None:
        """
        Persists a Grey Market Premium quote snapshot for an offering,
        and synchronizes published allotment_date and listing_date to the master record.

        Args:
            ipo_id: Unique identifier for the IPO.
            gmp_data: GMPData quote snapshot container.
        """
        with get_db_session(self.engine) as session:
            try:
                from ipo_platform.db.models import IPOMasterModel
                from sqlalchemy import select
                target_id = ipo_id
                exists = session.execute(select(IPOMasterModel.ipo_id).where(IPOMasterModel.ipo_id == ipo_id)).scalar()
                if not exists and "-" in ipo_id:
                    slug = ipo_id.split("-")[1]
                    matched = session.execute(
                        select(IPOMasterModel.ipo_id).where(
                            (IPOMasterModel.ipo_id.like(f"%{slug}%")) | (IPOMasterModel.ticker_symbol == slug)
                        )
                    ).scalar()
                    if matched:
                        target_id = matched

                # Check if target_id exists now; if not, create placeholder master record
                target_exists = session.execute(select(IPOMasterModel.ipo_id).where(IPOMasterModel.ipo_id == target_id)).scalar()
                if not target_exists:
                    from datetime import date, time, datetime
                    slug = target_id.split("-")[1] if "-" in target_id else target_id
                    company_title = (
                        getattr(gmp_data, "source", None)
                        if (getattr(gmp_data, "source", None) and getattr(gmp_data, "source") != "InvestorGain Live")
                        else f"{slug.title()} Limited"
                    )
                    ref_p = float(getattr(gmp_data, "reference_price", 100.0) or 100.0)
                    lot_sz = int(getattr(gmp_data, "lot_size", 50) or 50)
                    new_master = IPOMasterModel(
                        ipo_id=target_id,
                        company_name=company_title,
                        company_legal_name=f"{company_title} Limited",
                        ticker_symbol=slug,
                        segment="Mainboard",
                        sector="Diversified",
                        industry="Diversified",
                        status="Upcoming",
                        research_date=date.today(),
                        research_time=time(10, 0, 0),
                        data_cutoff=datetime.now(),
                        open_date=date.today(),
                        close_date=date.today(),
                        allotment_date=gmp_data.allotment_date,
                        listing_date=gmp_data.listing_date,
                        listing_status="Pre-Listing",
                        issue_size=100.0,
                        face_value=10.0,
                        price_band_high=ref_p,
                        price_band_low=ref_p,
                        lot_size=lot_sz,
                        minimum_investment=ref_p * lot_sz,
                        is_active=True,
                        version_id=1,
                    )
                    session.add(new_master)
                    session.flush()

                self.gmp_repo.save_gmp_snapshot(session, target_id, gmp_data)
                if gmp_data.allotment_date or gmp_data.listing_date:
                    self.write_repo.update_dates(
                        session,
                        target_id,
                        allotment_date=gmp_data.allotment_date,
                        listing_date=gmp_data.listing_date,
                    )
            except Exception as err:
                session.rollback()
                err_str = str(err).lower()
                if "foreign key" in err_str or "1452" in err_str:
                    return
                raise

