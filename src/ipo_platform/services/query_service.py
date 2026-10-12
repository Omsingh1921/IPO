"""
Application Query Service for Indian IPO Platform.
Acts as a facade encapsulating read-only queries, pagination, and GMP lookups over repositories.
"""

from typing import List, Optional, Union

from sqlalchemy import Engine

from ipo_platform.db.repository import GMPRepository, IPOReadRepository
from ipo_platform.db.session import get_db_session
from ipo_platform.models.enums import IPOStatusEnum
from ipo_platform.models.schema import GMPData, MasterIPORecord


class IPOQueryService:
    """Application Service facade managing read queries and data retrieval."""

    def __init__(
        self,
        engine: Engine,
        read_repo: type[IPOReadRepository] = IPOReadRepository,
        gmp_repo: type[GMPRepository] = GMPRepository,
    ) -> None:
        """
        Initializes IPOQueryService with dependency injection.

        Args:
            engine: SQLAlchemy Engine instance.
            read_repo: IPOReadRepository class or instance.
            gmp_repo: GMPRepository class or instance.
        """
        self.engine = engine
        self.read_repo = read_repo
        self.gmp_repo = gmp_repo

    def get_ipo_details(self, ipo_id: str) -> Optional[MasterIPORecord]:
        """
        Retrieves a MasterIPORecord aggregate by unique ipo_id.

        Args:
            ipo_id: Unique identifier for the IPO.

        Returns:
            MasterIPORecord if found, None otherwise.
        """
        with get_db_session(self.engine) as session:
            return self.read_repo.get_by_id(session, ipo_id)

    def get_ipo_by_slug(self, slug: str) -> Optional[MasterIPORecord]:
        """
        Retrieves a MasterIPORecord aggregate by slug or ticker symbol.

        Args:
            slug: Ticker symbol or ipo_id slug.

        Returns:
            MasterIPORecord if found, None otherwise.
        """
        with get_db_session(self.engine) as session:
            return self.read_repo.get_by_slug(session, slug)

    def list_active_ipos(self, skip: int = 0, limit: int = 100) -> List[MasterIPORecord]:
        """
        Lists all active MasterIPORecords with pagination.

        Args:
            skip: Offset number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of active MasterIPORecords.
        """
        with get_db_session(self.engine) as session:
            return self.read_repo.list_all(session, skip=skip, limit=limit)

    def list_ipos_by_status(
        self,
        status: Union[IPOStatusEnum, str],
        skip: int = 0,
        limit: int = 100,
    ) -> List[MasterIPORecord]:
        """
        Lists active MasterIPORecords filtered by offering status.

        Args:
            status: Offering status enum or string value.
            skip: Offset number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Filtered list of MasterIPORecords.
        """
        with get_db_session(self.engine) as session:
            return self.read_repo.list_by_status(session, status, skip=skip, limit=limit)

    def get_latest_gmp_quote(self, ipo_id: str) -> Optional[GMPData]:
        """
        Retrieves the latest Grey Market Premium quote for an IPO.

        Args:
            ipo_id: Unique identifier for the IPO.

        Returns:
            GMPData quote snapshot if found, None otherwise.
        """
        with get_db_session(self.engine) as session:
            return self.gmp_repo.get_latest_gmp(session, ipo_id)
