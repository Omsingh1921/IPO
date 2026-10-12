"""
Adapter Manager and Ingestion Orchestration for Indian IPO Platform.
Manages adapter lifecycle, health checks, multi-source synchronization,
and database persistence reusing IPOIngestionService, IPOWriteRepository, and GMPRepository.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Engine

from ipo_platform.adapters.base import AdapterSyncResult, BaseSourceAdapter
from ipo_platform.adapters.bse_adapter import BSEAdapter
from ipo_platform.adapters.gmp_adapter import GMPAdapter
from ipo_platform.adapters.nse_adapter import NSEAdapter
from ipo_platform.db import GMPRepository, IPOWriteRepository

if TYPE_CHECKING:
    from ipo_platform.services.ingestion_service import IPOIngestionService

logger = logging.getLogger(__name__)


@dataclass
class SourceSyncSummary:
    """Consolidated summary across all adapter synchronization runs."""
    total_sources: int = 0
    total_fetched: int = 0
    total_valid: int = 0
    master_records_ingested: int = 0
    gmp_quotes_recorded: int = 0
    errors: List[str] = field(default_factory=list)
    results_by_source: Dict[str, AdapterSyncResult] = field(default_factory=dict)
    dry_run: bool = False
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def is_successful(self) -> bool:
        return len(self.errors) == 0 or (self.master_records_ingested > 0 or self.gmp_quotes_recorded > 0)


class AdapterManager:
    """
    Coordinates and orchestrates upstream IPO data source adapters.
    Provides registration, health monitoring, error isolation, dry-run simulation,
    and dependency-injected atomic persistence.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        ingestion_service: Optional[Any] = None,
        write_repo: Optional[IPOWriteRepository] = None,
        gmp_repo: Optional[GMPRepository] = None,
        adapters: Optional[List[BaseSourceAdapter]] = None,
    ) -> None:
        """
        Initializes AdapterManager with dependency injection.

        Args:
            engine: Optional SQLAlchemy Engine instance.
            ingestion_service: Optional IPOIngestionService instance.
            write_repo: Optional IPOWriteRepository instance.
            gmp_repo: Optional GMPRepository instance.
            adapters: Optional initial list of BaseSourceAdapter instances.
        """
        self.engine = engine
        if ingestion_service is not None:
            self.ingestion_service = ingestion_service
        elif engine is not None:
            from ipo_platform.services.ingestion_service import IPOIngestionService
            self.ingestion_service = IPOIngestionService(engine)
        else:
            self.ingestion_service = None

        self.write_repo = write_repo
        self.gmp_repo = gmp_repo
        self._adapters: Dict[str, BaseSourceAdapter] = {}

        if adapters:
            for adapter in adapters:
                self.register_adapter(adapter)
        else:
            # Register standard adapters by default
            self.register_adapter(NSEAdapter())
            self.register_adapter(BSEAdapter())
            self.register_adapter(GMPAdapter())

    def register_adapter(self, adapter: BaseSourceAdapter) -> None:
        """Registers a data source adapter under its normalized name."""
        key = adapter.source_name.strip().lower()
        self._adapters[key] = adapter
        if "gmp" in key:
            self._adapters["gmp"] = adapter
        logger.debug("Registered adapter '%s' (%s)", key, adapter.__class__.__name__)

    def get_adapter(self, source_name: str) -> Optional[BaseSourceAdapter]:
        """Retrieves a registered adapter by source name."""
        return self._adapters.get(source_name.strip().lower())

    def list_adapters(self) -> List[str]:
        """Returns the list of uniquely registered adapter source names."""
        seen = set()
        names = []
        for name, adapter in self._adapters.items():
            if adapter.source_name not in seen:
                seen.add(adapter.source_name)
                names.append(adapter.source_name)
        return names

    def health_check_all(self) -> Dict[str, bool]:
        """
        Executes health check against all registered adapters.
        Returns mapping of source name to health boolean.
        """
        results: Dict[str, bool] = {}
        for name, adapter in self._adapters.items():
            if adapter.source_name in results:
                continue
            try:
                results[adapter.source_name] = adapter.health_check()
            except Exception as err:
                logger.warning("Health check failed for adapter '%s': %s", adapter.source_name, err)
                results[adapter.source_name] = False
        return results

    def sync_adapter(
        self,
        source_name: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        dry_run: bool = False,
    ) -> AdapterSyncResult:
        """
        Executes synchronization for an individual data source adapter.
        """
        adapter = self.get_adapter(source_name)
        if not adapter:
            res = AdapterSyncResult(source_name=source_name)
            res.errors.append(f"Unknown or unconfigured adapter: '{source_name}'")
            return res

        logger.info("Executing sync for '%s' (dry_run=%s, limit=%d)", source_name, dry_run, limit)
        result = adapter.sync(from_date=from_date, to_date=to_date, limit=limit)

        if not dry_run and self.ingestion_service:
            # Persist master records respecting OCC protections
            for rec in result.master_records:
                try:
                    self.ingestion_service.ingest_master_record(rec)
                    logger.debug("Ingested live master record: %s", rec.ipo_entity.ipo_id)
                except Exception as err:
                    err_msg = f"Failed to persist master record {rec.ipo_entity.ipo_id}: {err}"
                    logger.error(err_msg)
                    result.errors.append(err_msg)

            # Persist GMP quotes
            for ipo_id, gmp_data in result.gmp_quotes:
                try:
                    self.ingestion_service.record_gmp_quote(ipo_id, gmp_data)
                    logger.debug("Recorded live GMP quote for: %s", ipo_id)
                except Exception as err:
                    err_msg = f"Failed to persist GMP quote for {ipo_id}: {err}"
                    logger.error(err_msg)
                    result.errors.append(err_msg)

        return result

    def orchestrate_sync(
        self,
        sources: Optional[List[str]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        dry_run: bool = False,
    ) -> SourceSyncSummary:
        """
        Orchestrates multi-source ingestion pipeline across specified or all registered sources.
        """
        summary = SourceSyncSummary(dry_run=dry_run)
        target_keys = (
            [s.strip().lower() for s in sources]
            if sources
            else list(self._adapters.keys())
        )

        # Deduplicate keys pointing to same adapter
        targeted_adapters: Dict[str, BaseSourceAdapter] = {}
        for key in target_keys:
            adapter = self.get_adapter(key)
            if adapter:
                targeted_adapters[adapter.source_name.lower()] = adapter
            else:
                err_msg = f"Unknown or unconfigured adapter: '{key}'"
                summary.errors.append(err_msg)

        summary.total_sources = len(targeted_adapters)

        for src_key, adapter in targeted_adapters.items():
            res = self.sync_adapter(
                source_name=src_key,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
                dry_run=dry_run,
            )
            summary.results_by_source[src_key] = res
            summary.total_fetched += res.records_fetched
            summary.total_valid += res.records_valid
            summary.master_records_ingested += len(res.master_records)
            summary.gmp_quotes_recorded += len(res.gmp_quotes)
            summary.errors.extend(res.errors)

        summary.completed_at = datetime.utcnow()
        return summary
