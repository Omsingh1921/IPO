"""
Scheduler Management and Execution Audit API Endpoints (Phase 1).
Exposes GET /scheduler/history for execution audits and POST /scheduler/trigger-sync
for manual on-demand market hours synchronization triggers.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from ipo_platform.api.dependencies import get_db_engine
from ipo_platform.db.session import get_db_session
from ipo_platform.jobs.execution_history import JobExecutionHistoryRepository
from ipo_platform.jobs.live_sync_job import run_live_market_sync_job
from ipo_platform.security.rate_limiter import rate_limit
from ipo_platform.security.rbac import Role, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


class JobExecutionLogItem(BaseModel):
    id: int
    job_name: str
    execution_date: str
    started_at: str
    completed_at: Optional[str] = None
    node_id: str
    execution_status: str
    error_message: Optional[str] = None


class JobExecutionHistoryResponse(BaseModel):
    total: int
    executions: List[JobExecutionLogItem]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TriggerSyncResponse(BaseModel):
    status: str
    job_name: str
    execution_date: str
    master_records_ingested: int
    gmp_quotes_recorded: int
    duration_seconds: float
    errors: List[str] = []
    timestamp: Optional[str] = None


@router.get(
    "/history",
    response_model=JobExecutionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scheduled Job Execution History",
    description="Retrieves persistent audit records of scheduled market sync runs from MySQL table scheduled_job_executions.",
    dependencies=[Depends(rate_limit(endpoint_tag="/scheduler/history"))],
)
def get_execution_history(
    limit: int = Query(default=20, ge=1, le=100),
    engine: Any = Depends(get_db_engine),
    _user: Any = Depends(require_role(Role.READ_ONLY)),
) -> JobExecutionHistoryResponse:
    """Retrieves recent scheduled job executions ordered newest to oldest."""
    with get_db_session(engine) as session:
        records = JobExecutionHistoryRepository.get_recent_executions(session, limit=limit)
        items = [
            JobExecutionLogItem(
                id=r.id,
                job_name=r.job_name,
                execution_date=r.execution_date.isoformat(),
                started_at=r.started_at.isoformat() if r.started_at else "",
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
                node_id=r.node_id,
                execution_status=r.execution_status,
                error_message=r.error_message,
            )
            for r in records
        ]
        return JobExecutionHistoryResponse(total=len(items), executions=items)


@router.post(
    "/trigger-sync",
    response_model=TriggerSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger On-Demand Live Market Sync",
    description="Executes a live market sync immediately across BSE, NSE, and GMP, persisting state to scheduled_job_executions.",
    dependencies=[Depends(rate_limit(endpoint_tag="/scheduler/trigger-sync"))],
)
def trigger_sync_now(
    dry_run: bool = Query(default=False),
    force_weekend: bool = Query(default=False, description="Bypass weekend market closure check if True"),
    engine: Any = Depends(get_db_engine),
    _user: Any = Depends(require_role(Role.OPERATOR)),
) -> TriggerSyncResponse:
    """Triggers live synchronization and records execution in database."""
    res = run_live_market_sync_job(
        engine=engine,
        dry_run=dry_run,
        check_trading_day=not force_weekend,
        node_id="manual-api-trigger",
    )
    return TriggerSyncResponse(
        status=res.get("status", "UNKNOWN"),
        job_name=res.get("job_name", "manual_sync"),
        execution_date=res.get("execution_date", datetime.utcnow().strftime("%Y-%m-%d")),
        master_records_ingested=res.get("master_records_ingested", 0),
        gmp_quotes_recorded=res.get("gmp_quotes_recorded", 0),
        duration_seconds=res.get("duration_seconds", 0.0),
        errors=res.get("errors", []),
        timestamp=res.get("timestamp"),
    )
