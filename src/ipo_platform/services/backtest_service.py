"""
Application Backtest Service for Indian IPO Platform.
Acts as a facade encapsulating historical outcomes persistence, longitudinal event streams, and backtesting execution.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import Engine

from ipo_platform.db.repository import BacktestRepository, IPOReadRepository
from ipo_platform.db.session import get_db_session
from ipo_platform.backtest.backtest_engine import BacktestEngine
from ipo_platform.models.schema import HistoricalIPO, MasterIPORecord, PerformanceEvent


class IPOBacktestService:
    """Application Service facade managing backtesting evaluation and historical outcome tracking."""

    def __init__(
        self,
        engine: Engine,
        backtest_repo: type[BacktestRepository] = BacktestRepository,
        read_repo: type[IPOReadRepository] = IPOReadRepository,
    ) -> None:
        """
        Initializes IPOBacktestService with dependency injection.

        Args:
            engine: SQLAlchemy Engine instance.
            backtest_repo: BacktestRepository class or instance.
            read_repo: IPOReadRepository class or instance.
        """
        self.engine = engine
        self.backtest_repo = backtest_repo
        self.read_repo = read_repo

    def record_historical_outcome(self, ipo_id: str, hist_data: HistoricalIPO) -> HistoricalIPO:
        """
        Persists post-listing historical performance outcome metrics for an IPO.

        Args:
            ipo_id: Unique identifier for the IPO.
            hist_data: HistoricalIPO performance metrics dataclass.

        Returns:
            Persisted HistoricalIPO container.
        """
        with get_db_session(self.engine) as session:
            self.backtest_repo.save_historical_performance(session, ipo_id, hist_data)
            return self.get_historical_outcome(ipo_id) or hist_data

    def get_historical_outcome(self, ipo_id: str) -> Optional[HistoricalIPO]:
        """
        Retrieves post-listing historical performance outcome for an IPO.

        Args:
            ipo_id: Unique identifier for the IPO.

        Returns:
            HistoricalIPO container if found, None otherwise.
        """
        with get_db_session(self.engine) as session:
            return self.backtest_repo.get_historical_performance(session, ipo_id)

    def record_price_event(self, ipo_id: str, event: PerformanceEvent) -> PerformanceEvent:
        """
        Persists a longitudinal post-listing price event stream entry.

        Args:
            ipo_id: Unique identifier for the IPO.
            event: PerformanceEvent container.

        Returns:
            Persisted PerformanceEvent container.
        """
        with get_db_session(self.engine) as session:
            self.backtest_repo.save_performance_event(session, ipo_id, event)
            return event

    def list_price_events(self, ipo_id: str) -> List[PerformanceEvent]:
        """
        Lists all longitudinal price events for an IPO ordered by days_from_listing.

        Args:
            ipo_id: Unique identifier for the IPO.

        Returns:
            List of PerformanceEvents.
        """
        with get_db_session(self.engine) as session:
            return self.backtest_repo.list_performance_events(session, ipo_id)

    def run_backtest_simulation(self, ipo_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Loads records from database and runs backtesting analysis via BacktestEngine.

        Args:
            ipo_ids: Optional list of specific IPO IDs to backtest. If None, backtests all active IPOs.

        Returns:
            Backtest simulation results dictionary.
        """
        records: List[MasterIPORecord] = []
        with get_db_session(self.engine) as session:
            if ipo_ids:
                for ipo_id in ipo_ids:
                    rec = self.read_repo.get_by_id(session, ipo_id)
                    if rec:
                        records.append(rec)
            else:
                records = self.read_repo.list_all(session, skip=0, limit=1000)

        return BacktestEngine.run_backtest(records)
