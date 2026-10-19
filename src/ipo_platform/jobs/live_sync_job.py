"""
Market Hours Live Market Synchronization Job Runner for Indian IPO Platform.
Executes multi-source live synchronization across BSE, NSE, and InvestorGain GMP
at strategic market hours (09:15 Market Open, 13:00 Mid-Day, 17:00 Market Close IST).
Enforces trading calendar validation, execution state auditing, and error isolation.
"""

from datetime import date, datetime, timedelta, timezone
import logging
import os
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine

from ipo_platform.db.session import get_db_session
from ipo_platform.jobs.execution_history import (
    JobExecutionHistoryRepository,
    JobExecutionStatus,
)
from ipo_platform.services.sync_service import SourceSyncService, SourceSyncSummary

logger = logging.getLogger(__name__)

# Standard Indian Standard Time (IST = UTC+05:30)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")

# Default market hour synchronization slots (HH:MM IST)
DEFAULT_MARKET_HOURS_SLOTS = ["09:15", "13:00", "17:00"]


def is_market_trading_day(target_date: Optional[date] = None, tz: Optional[timezone] = None) -> bool:
    """
    Evaluates whether the specified date is an active Indian stock market trading day.
    Excludes weekend days (Saturday and Sunday).

    Args:
        target_date: Optional calendar date to evaluate (defaults to today in IST).
        tz: Timezone for date calculation (defaults to IST).

    Returns:
        True if the day is a weekday (Monday-Friday), False if weekend.
    """
    eval_tz = tz or IST_TIMEZONE
    eval_date = target_date or datetime.now(eval_tz).date()
    # Monday=0, Tuesday=1, ..., Friday=4, Saturday=5, Sunday=6
    return eval_date.weekday() < 5


def run_live_market_sync_job(
    engine: Engine,
    dry_run: bool = False,
    job_name: Optional[str] = None,
    check_trading_day: bool = True,
    node_id: Optional[str] = None,
    tz: Optional[timezone] = None,
) -> Dict[str, Any]:
    """
    Executes live market synchronization across BSE, NSE, and GMP feeds with audit tracking.
    Records execution lifecycle states (STARTED, COMPLETED, FAILED, SKIPPED) in MySQL
    table `scheduled_job_executions`.

    Args:
        engine: SQLAlchemy Engine instance.
        dry_run: If True, simulates pipeline without persisting updates.
        job_name: Unique task identifier (e.g. 'market_sync_0915').
        check_trading_day: If True, skips execution on weekend non-trading days.
        node_id: Node or worker identifier performing execution.
        tz: Timezone for execution evaluation (defaults to IST).

    Returns:
        Execution report dictionary with ingestion counts, timestamps, and status.
    """
    eval_tz = tz or IST_TIMEZONE
    now_ist = datetime.now(eval_tz)
    exec_date = now_ist.date()
    effective_job_name = job_name or f"market_sync_{now_ist.strftime('%H%M')}"
    effective_node_id = node_id or f"scheduler-{os.getenv('HOSTNAME', 'local')}"

    # 1. Trading Day Validation Guard
    if check_trading_day and not is_market_trading_day(exec_date, tz=eval_tz):
        day_name = now_ist.strftime("%A")
        logger.info(
            "Scheduled job '%s' skipped on %s: %s is a non-trading weekend day.",
            effective_job_name,
            exec_date,
            day_name,
        )
        with get_db_session(engine) as session:
            JobExecutionHistoryRepository.record_start(
                session, effective_job_name, exec_date, effective_node_id
            )
            JobExecutionHistoryRepository.record_skipped(
                session, effective_job_name, exec_date, f"Non-trading day ({day_name})"
            )

        return {
            "status": JobExecutionStatus.SKIPPED.value,
            "job_name": effective_job_name,
            "execution_date": exec_date.isoformat(),
            "reason": f"Non-trading day ({day_name})",
            "master_records_ingested": 0,
            "gmp_quotes_recorded": 0,
            "errors": [],
            "duration_seconds": 0.0,
        }

    # 2. Record STARTED State in Database
    with get_db_session(engine) as session:
        JobExecutionHistoryRepository.record_start(
            session, effective_job_name, exec_date, effective_node_id
        )

    start_perf = time.perf_counter()
    logger.info(
        "Beginning live market sync execution '%s' on %s (node: %s, dry_run: %s)...",
        effective_job_name,
        exec_date,
        effective_node_id,
        dry_run,
    )

    try:
        # 3. Execute Live Ingestion & Normalization
        sync_service = SourceSyncService(engine)
        summary: SourceSyncSummary = sync_service.sync_all(limit=50, dry_run=dry_run)
        duration_sec = round(time.perf_counter() - start_perf, 2)

        # 4. Record COMPLETED State
        with get_db_session(engine) as session:
            JobExecutionHistoryRepository.record_completion(session, effective_job_name, exec_date)

        logger.info(
            "Live market sync '%s' COMPLETED in %.2fs: %d master records ingested/updated, %d GMP quotes recorded.",
            effective_job_name,
            duration_sec,
            summary.master_records_ingested,
            summary.gmp_quotes_recorded,
        )

        return {
            "status": JobExecutionStatus.COMPLETED.value,
            "job_name": effective_job_name,
            "execution_date": exec_date.isoformat(),
            "master_records_ingested": summary.master_records_ingested,
            "gmp_quotes_recorded": summary.gmp_quotes_recorded,
            "duration_seconds": duration_sec,
            "errors": summary.errors,
            "timestamp": now_ist.isoformat(),
        }

    except Exception as exc:
        duration_sec = round(time.perf_counter() - start_perf, 2)
        err_msg = str(exc)
        logger.error(
            "Live market sync '%s' FAILED after %.2fs: %s",
            effective_job_name,
            duration_sec,
            err_msg,
            exc_info=True,
        )
        with get_db_session(engine) as session:
            JobExecutionHistoryRepository.record_failure(
                session, effective_job_name, exec_date, err_msg
            )

        return {
            "status": JobExecutionStatus.FAILED.value,
            "job_name": effective_job_name,
            "execution_date": exec_date.isoformat(),
            "master_records_ingested": 0,
            "gmp_quotes_recorded": 0,
            "duration_seconds": duration_sec,
            "errors": [err_msg],
            "timestamp": now_ist.isoformat(),
        }
