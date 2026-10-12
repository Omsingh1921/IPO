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
        Persists a Grey Market Premium quote snapshot for an offering.

        Args:
            ipo_id: Unique identifier for the IPO.
            gmp_data: GMPData quote snapshot container.
        """
        with get_db_session(self.engine) as session:
            self.gmp_repo.save_gmp_snapshot(session, ipo_id, gmp_data)
