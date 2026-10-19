"""
Job Execution History Persistence and Audit Repository for Indian IPO Platform.
Maintains persistent records of scheduled job execution states in relational storage,
enforcing exactly-once execution per day and tracking node execution metrics.
"""

from datetime import date, datetime
from enum import Enum
import logging
from typing import List, Optional

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from ipo_platform.db.models import ScheduledJobExecutionModel
from ipo_platform.db.session import get_db_session

logger = logging.getLogger(__name__)


class JobExecutionStatus(str, Enum):
    """Lifecycle statuses for scheduled job execution."""
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class JobExecutionHistoryRepository:
    """Repository handling execution state persistence and idempotency verification."""

    @staticmethod
    def get_execution(
        session: Session,
        job_name: str,
        execution_date: date,
    ) -> Optional[ScheduledJobExecutionModel]:
        """Retrieves existing execution record for a job and date."""
        stmt = select(ScheduledJobExecutionModel).where(
            ScheduledJobExecutionModel.job_name == job_name,
            ScheduledJobExecutionModel.execution_date == execution_date,
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def record_start(
        session: Session,
        job_name: str,
        execution_date: date,
        node_id: str,
    ) -> ScheduledJobExecutionModel:
        """
        Creates or updates execution state to STARTED.
        """
        record = JobExecutionHistoryRepository.get_execution(session, job_name, execution_date)
        now = datetime.utcnow()
        if record is None:
            record = ScheduledJobExecutionModel(
                job_name=job_name,
                execution_date=execution_date,
                started_at=now,
                node_id=node_id,
                execution_status=JobExecutionStatus.STARTED.value,
            )
            session.add(record)
        else:
            record.started_at = now
            record.node_id = node_id
            record.execution_status = JobExecutionStatus.STARTED.value
            record.error_message = None

        session.flush()
        return record

    @staticmethod
    def record_completion(
        session: Session,
        job_name: str,
        execution_date: date,
    ) -> Optional[ScheduledJobExecutionModel]:
        """Marks execution state as COMPLETED."""
        record = JobExecutionHistoryRepository.get_execution(session, job_name, execution_date)
        if record:
            record.completed_at = datetime.utcnow()
            record.execution_status = JobExecutionStatus.COMPLETED.value
            session.flush()
        return record

    @staticmethod
    def record_failure(
        session: Session,
        job_name: str,
        execution_date: date,
        error_message: str,
    ) -> Optional[ScheduledJobExecutionModel]:
        """Marks execution state as FAILED with error details."""
        record = JobExecutionHistoryRepository.get_execution(session, job_name, execution_date)
        if record:
            record.completed_at = datetime.utcnow()
            record.execution_status = JobExecutionStatus.FAILED.value
            record.error_message = str(error_message)[:1000]
            session.flush()
        return record

    @staticmethod
    def record_skipped(
        session: Session,
        job_name: str,
        execution_date: date,
        reason: str,
    ) -> Optional[ScheduledJobExecutionModel]:
        """Marks execution state as SKIPPED with reason details."""
        record = JobExecutionHistoryRepository.get_execution(session, job_name, execution_date)
        if record:
            record.completed_at = datetime.utcnow()
            record.execution_status = JobExecutionStatus.SKIPPED.value
            record.error_message = str(reason)[:1000]
            session.flush()
        return record

    @staticmethod
    def is_already_completed(
        session: Session,
        job_name: str,
        execution_date: date,
    ) -> bool:
        """Returns True if the job has already completed successfully for the given date."""
        record = JobExecutionHistoryRepository.get_execution(session, job_name, execution_date)
        return record is not None and record.execution_status == JobExecutionStatus.COMPLETED.value

    @staticmethod
    def get_recent_executions(
        session: Session,
        limit: int = 20,
    ) -> List[ScheduledJobExecutionModel]:
        """Retrieves recent job execution audit records ordered chronologically descending."""
        stmt = (
            select(ScheduledJobExecutionModel)
            .order_by(ScheduledJobExecutionModel.started_at.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())
