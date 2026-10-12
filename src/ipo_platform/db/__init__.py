"""
Database schema and ORM persistence package for Indian IPO Platform.
"""

from ipo_platform.db.base import Base
from ipo_platform.db.exceptions import (
    ConstraintViolationError,
    DatabaseConnectionError,
    DataIntegrityError,
    DuplicateIPOSlugError,
    OptimisticLockError,
    PlatformDatabaseError,
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
from ipo_platform.db.repository import (
    BacktestRepository,
    GMPRepository,
    IPOReadRepository,
    IPOWriteRepository,
)
from ipo_platform.db.session import (
    get_db_session,
    get_engine,
    get_session_factory,
    init_db,
)

__all__ = [
    "Base",
    "PlatformDatabaseError",
    "DatabaseConnectionError",
    "DuplicateIPOSlugError",
    "OptimisticLockError",
    "ConstraintViolationError",
    "DataIntegrityError",
    "SourceModel",
    "IPOMasterModel",
    "ObjectOfIssueModel",
    "FinancialModel",
    "ValuationModel",
    "SubscriptionModel",
    "AnchorHeaderModel",
    "AnchorInvestorModel",
    "GMPLogModel",
    "PeerCompanyModel",
    "RiskDisclosureModel",
    "ScenarioModel",
    "HistoricalPerformanceModel",
    "PerformanceEventModel",
    "MasterIPOMapper",
    "IPOReadRepository",
    "IPOWriteRepository",
    "GMPRepository",
    "BacktestRepository",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "init_db",
]
