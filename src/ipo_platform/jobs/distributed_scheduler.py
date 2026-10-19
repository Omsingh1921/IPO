"""
Distributed Job Scheduler for Indian IPO Platform.
Orchestrates scheduled tasks across distributed worker nodes, providing distributed locking,
persistent execution state tracking, crash recovery, and exactly-once daily execution guarantees.
"""

from datetime import date, datetime, timedelta, timezone
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import uuid

from sqlalchemy import Engine

from ipo_platform.db.session import get_db_session
from ipo_platform.jobs.execution_history import (
    JobExecutionHistoryRepository,
    JobExecutionStatus,
)
from ipo_platform.jobs.locks import DistributedLock, RedisDistributedLock

logger = logging.getLogger(__name__)

# Indian Standard Time (IST = UTC+05:30)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


class DistributedJobScheduler:
    """
    Distributed Job Scheduler supporting multi-node cluster coordination,
    distributed Redis locks, and relational execution history idempotency.
    """

    def __init__(
        self,
        engine: Engine,
        lock_factory: Optional[Callable[[str], DistributedLock]] = None,
        node_id: Optional[str] = None,
        tz: Optional[timezone] = None,
    ) -> None:
        """
        Initializes DistributedJobScheduler with dependency injection.

        Args:
            engine: SQLAlchemy Engine instance for execution history persistence.
            lock_factory: Callable returning DistributedLock for a given lock name.
            node_id: Unique identifier for this worker instance (defaults to hostname-UUID).
            tz: Timezone for execution evaluation (defaults to IST).
        """
        self.engine = engine
        self.node_id = node_id or f"node-{os.uname().nodename if hasattr(os, 'uname') else 'worker'}-{uuid.uuid4().hex[:8]}"
        self.tz = tz or IST_TIMEZONE
        self.lock_factory = lock_factory or (lambda name: RedisDistributedLock(name))

        self._lock = threading.RLock()
        self._scheduled_threads: Dict[str, threading.Thread] = {}
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def get_scheduled_jobs(self) -> List[str]:
        with self._lock:
            return list(self._scheduled_threads.keys())

    def execute_job_with_idempotency(
        self,
        job_name: str,
        job_func: Callable[..., Any],
        target_date: Optional[date] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Executes a job with distributed locking and database execution history checks,
        enforcing exactly-once execution for the target date.

        Args:
            job_name: Unique task identifier.
            job_func: Callable target job function.
            target_date: Target execution calendar date (defaults to today in configured timezone).
            *args: Positional arguments for target job.
            **kwargs: Keyword arguments for target job.

        Returns:
            Dictionary with execution summary: {"status": ..., "message": ..., "result": ...}
        """
        exec_date = target_date or datetime.now(self.tz).date()
        lock_name = f"{job_name}-{exec_date.isoformat()}"
        lock = self.lock_factory(lock_name)

        logger.info("Node '%s' attempting distributed lock for job '%s' on %s", self.node_id, job_name, exec_date)
        if not lock.acquire(blocking=False):
            logger.info("Job '%s' for %s is locked by another node or active worker. Skipping.", job_name, exec_date)
            return {
                "status": JobExecutionStatus.SKIPPED.value,
                "message": f"Lock contention: job '{job_name}' currently executing on another node.",
                "result": None,
            }

        try:
            # 1. Check if already completed in execution history
            with get_db_session(self.engine) as session:
                if JobExecutionHistoryRepository.is_already_completed(session, job_name, exec_date):
                    logger.info("Job '%s' has already completed for date %s. Idempotency preserved.", job_name, exec_date)
                    return {
                        "status": JobExecutionStatus.SKIPPED.value,
                        "message": f"Job '{job_name}' already completed for date {exec_date}.",
                        "result": None,
                    }

                # 2. Record STARTED status
                JobExecutionHistoryRepository.record_start(session, job_name, exec_date, self.node_id)

            # 3. Execute the actual job function
            logger.info("Node '%s' running job '%s' for date %s...", self.node_id, job_name, exec_date)
            res = job_func(*args, **kwargs)

            # 4. Mark COMPLETED
            with get_db_session(self.engine) as session:
                JobExecutionHistoryRepository.record_completion(session, job_name, exec_date)
                logger.info("Job '%s' marked COMPLETED in database for %s", job_name, exec_date)

            return {
                "status": JobExecutionStatus.COMPLETED.value,
                "message": f"Job '{job_name}' executed successfully.",
                "result": res,
            }

        except Exception as err:
            logger.error("Job '%s' failed during execution: %s", job_name, err, exc_info=True)
            with get_db_session(self.engine) as session:
                JobExecutionHistoryRepository.record_failure(session, job_name, exec_date, str(err))

            return {
                "status": JobExecutionStatus.FAILED.value,
                "message": f"Job failed: {err}",
                "result": None,
            }

        finally:
            try:
                lock.release()
            except Exception as lock_err:
                logger.warning("Error releasing lock '%s': %s", lock_name, lock_err)

    def schedule_daily_job(
        self,
        job_name: str,
        job_func: Callable[..., Any],
        execution_time: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Schedules a daily distributed recurring job loop.
        """
        target_exec_time = execution_time or os.getenv("BRIEFING_EXECUTION_TIME", "12:01")

        with self._lock:
            if job_name in self._scheduled_threads:
                logger.warning("Job '%s' is already registered in distributed scheduler.", job_name)
                return

            self._is_running = True

        def _worker_loop() -> None:
            logger.info("Starting distributed worker loop for '%s' (daily at %s %s)", job_name, target_exec_time, self.tz.tzname(None))
            while True:
                with self._lock:
                    if not self._is_running:
                        break

                now = datetime.now(self.tz)
                target_hour, target_minute = map(int, target_exec_time.split(":"))
                target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

                # Check database to see if job already completed today
                with get_db_session(self.engine) as session:
                    already_completed = JobExecutionHistoryRepository.is_already_completed(session, job_name, now.date())

                if now >= target_dt or already_completed:
                    target_dt += timedelta(days=1)

                seconds_until_target = max(0.0, (target_dt - now).total_seconds())

                slept = 0.0
                while slept < seconds_until_target:
                    with self._lock:
                        if not self._is_running:
                            return
                    sleep_chunk = min(0.5, seconds_until_target - slept)
                    time.sleep(sleep_chunk)
                    slept += sleep_chunk

                with self._lock:
                    should_run = self._is_running

                if should_run:
                    self.execute_job_with_idempotency(job_name, job_func, *args, **kwargs)

        with self._lock:
            thread = threading.Thread(target=_worker_loop, name=f"dist-scheduler-{job_name}", daemon=True)
            self._scheduled_threads[job_name] = thread
            thread.start()

    def schedule_market_hours_sync(
        self,
        execution_times: Optional[List[str]] = None,
        check_trading_day: bool = True,
        dry_run: bool = False,
    ) -> List[str]:
        """
        Schedules automated market-hours synchronization across BSE, NSE, and GMP
        in a distributed cluster environment enforcing idempotency and distributed locks.
        Defaults to 09:15 Market Open, 13:00 Mid-Day, 17:00 Market Close IST.
        """
        from ipo_platform.jobs.live_sync_job import DEFAULT_MARKET_HOURS_SLOTS, run_live_market_sync_job

        slots = execution_times or DEFAULT_MARKET_HOURS_SLOTS
        registered = []

        for slot_time in slots:
            slot_clean = slot_time.strip()
            job_name = f"market_sync_{slot_clean.replace(':', '')}"

            def _create_slot_runner(j_name: str):
                return lambda: run_live_market_sync_job(
                    engine=self.engine,
                    dry_run=dry_run,
                    job_name=j_name,
                    check_trading_day=check_trading_day,
                    node_id=self.node_id,
                    tz=self.tz,
                )

            self.schedule_daily_job(
                job_name=job_name,
                job_func=_create_slot_runner(job_name),
                execution_time=slot_clean,
            )
            registered.append(job_name)

        logger.info("Distributed market hours synchronization scheduled for IST slots: %s", registered)
        return registered

    def stop_all(self) -> None:
        """Stops all background scheduler loops safely."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            threads_to_join = list(self._scheduled_threads.values())
            self._scheduled_threads.clear()

        for t in threads_to_join:
            t.join(timeout=2.0)
        logger.info("All distributed scheduler worker threads stopped.")
