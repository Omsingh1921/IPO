"""
Source Synchronization Service for Indian IPO Platform.
Orchestrates multi-source ingestion across NSE, BSE, and GMP adapters,
handling partial failures, deduplication, dry-run simulation, and atomic persistence.
"""

from datetime import date
import logging
from typing import List, Optional

from sqlalchemy import Engine

from ipo_platform.adapters.adapter_manager import AdapterManager, SourceSyncSummary
from ipo_platform.adapters.base import AdapterSyncResult, BaseSourceAdapter
from ipo_platform.services.ingestion_service import IPOIngestionService

logger = logging.getLogger(__name__)

__all__ = ["SourceSyncSummary", "SourceSyncService"]


class SourceSyncService:
    """
    Application Service facade managing synchronization across external upstream feeds.
    Reuses AdapterManager and IPOIngestionService for database persistence, respecting OCC/version_id protections.
    """

    def __init__(
        self,
        engine: Engine,
        ingestion_service: Optional[IPOIngestionService] = None,
        adapters: Optional[List[BaseSourceAdapter]] = None,
    ) -> None:
        """
        Initializes SourceSyncService with dependency injection.

        Args:
            engine: SQLAlchemy Engine instance.
            ingestion_service: Optional IPOIngestionService instance.
            adapters: Optional list of pre-configured BaseSourceAdapter instances.
        """
        self.engine = engine
        self.ingestion_service = ingestion_service or IPOIngestionService(engine)
        self.manager = AdapterManager(
            engine=self.engine,
            ingestion_service=self.ingestion_service,
            adapters=adapters,
        )
        self.adapters = self.manager._adapters

    def sync_source(
        self,
        source_name: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        dry_run: bool = False,
    ) -> AdapterSyncResult:
        """
        Synchronizes an individual data source by name.
        """
        return self.manager.sync_adapter(
            source_name=source_name,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            dry_run=dry_run,
        )

    def sync_all(
        self,
        sources: Optional[List[str]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        dry_run: bool = False,
    ) -> SourceSyncSummary:
        """
        Synchronizes all specified or registered sources.
        """
        return self.manager.orchestrate_sync(
            sources=sources,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            dry_run=dry_run,
        )
