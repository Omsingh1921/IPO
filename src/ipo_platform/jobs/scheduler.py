"""
Job Scheduler Infrastructure for Indian IPO Platform.
Provides lightweight job scheduling supporting both manual on-demand triggering
and scheduled execution.

Architecture & Operational Characteristics:
- Timezone Awareness: Evaluates scheduled targets against Indian Standard Time (IST, UTC+05:30).
  Falls back to local machine time if explicit zoneinfo is not installed or configured.
- Execution Guard: Prevents duplicate execution per day via monotonic date tracking.
- Thread Safety: Protects schedule registration, loop lifecycle, and thread cleanup with a Reentrant Lock (RLock).
- Resiliency: Exceptions within scheduled jobs are captured and logged to prevent worker loop crashes.
- Lifecycle & Process Restarts: In-memory scheduler. Scheduled jobs are not persisted across process restarts.
  In production distributed environments, pairing with an external orchestrator (systemd timer, cron, or Celery)
  is recommended.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Standard Indian Standard Time (IST = UTC+05:30)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


class JobScheduler:
    """Lightweight Job Scheduler supporting manual execution and scheduled triggers."""

    def __init__(self, tz: Optional[timezone] = None) -> None:
        """
        Initializes JobScheduler instance.

        Args:
            tz: Optional timezone to evaluate execution against (defaults to IST).
        """
        self.tz = tz or IST_TIMEZONE
        self._lock = threading.RLock()
        self._scheduled_threads: Dict[str, threading.Thread] = {}
        self._is_running: bool = False
        self._last_run_dates: Dict[str, str] = {}

    @property
    def is_running(self) -> bool:
        """Returns True if the scheduler has active running worker loops."""
        with self._lock:
            return self._is_running

    def get_scheduled_jobs(self) -> List[str]:
        """Returns the list of currently scheduled job names."""
        with self._lock:
            return list(self._scheduled_threads.keys())

    @staticmethod
    def run_job_now(job_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Executes a job function immediately (manual trigger mode).

        Args:
            job_func: Callable target job function.
            *args: Positional arguments passed to job function.
            **kwargs: Keyword arguments passed to job function.

        Returns:
            Return value of job function execution.
        """
        func_name = getattr(job_func, "__name__", str(job_func))
        logger.info("Manual execution triggered for job: %s", func_name)
        return job_func(*args, **kwargs)

    def schedule_daily_job(
        self,
        job_name: str,
        job_func: Callable[..., Any],
        execution_time: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Schedules a daily recurring job execution at the specified target time (HH:MM IST).

        Args:
            job_name: Unique identifier string for the scheduled job thread.
            job_func: Callable target job function.
            execution_time: Target execution time string (HH:MM in 24h format, defaults to BRIEFING_EXECUTION_TIME or 12:01).
            *args: Positional arguments passed to job function.
            **kwargs: Keyword arguments passed to job function.
        """
        target_exec_time = execution_time or os.getenv("BRIEFING_EXECUTION_TIME", "12:01")

        with self._lock:
            if job_name in self._scheduled_threads:
                logger.warning("Job '%s' is already scheduled. Ignoring duplicate schedule request.", job_name)
                return

            self._is_running = True

        def _scheduler_loop() -> None:
            logger.info(
                "Job '%s' scheduled for daily execution at %s %s",
                job_name,
                target_exec_time,
                self.tz.tzname(None) if self.tz else "Local",
            )
            while True:
                with self._lock:
                    if not self._is_running:
                        break

                now = datetime.now(self.tz)
                target_hour, target_minute = map(int, target_exec_time.split(":"))
                target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

                # If time today has passed or job already ran today, advance to next day
                today_str = now.strftime("%Y-%m-%d")
                with self._lock:
                    already_ran_today = self._last_run_dates.get(job_name) == today_str

                if now >= target_dt or already_ran_today:
                    target_dt += timedelta(days=1)

                seconds_until_target = max(0.0, (target_dt - now).total_seconds())
                logger.info(
                    "Job '%s' sleeping for %.1f seconds until next run at %s",
                    job_name,
                    seconds_until_target,
                    target_dt,
                )

                # Sleep in short intervals to allow prompt and clean cancellation on stop_all()
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
                    current_run_date = datetime.now(self.tz).strftime("%Y-%m-%d")
                    with self._lock:
                        if self._last_run_dates.get(job_name) == current_run_date:
                            logger.info("Job '%s' already executed on %s. Skipping duplicate trigger.", job_name, current_run_date)
                            continue
                        self._last_run_dates[job_name] = current_run_date

                    try:
                        logger.info("Triggering scheduled job run: %s", job_name)
                        job_func(*args, **kwargs)
                    except Exception as err:
                        logger.error("Error executing scheduled job '%s': %s", job_name, err, exc_info=True)

        with self._lock:
            thread = threading.Thread(target=_scheduler_loop, name=f"scheduler-{job_name}", daemon=True)
            self._scheduled_threads[job_name] = thread
            thread.start()

    def schedule_interval_job(
        self,
        job_name: str,
        job_func: Callable[..., Any],
        interval_seconds: float = 300.0,
        run_immediately: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Schedules a recurring interval job execution (e.g. every 5 minutes).

        Args:
            job_name: Unique identifier string for the scheduled job thread.
            job_func: Callable target job function.
            interval_seconds: Delay in seconds between successive executions (defaults to 300.0).
            run_immediately: If True, executes once immediately upon scheduling before the first sleep.
            *args: Positional arguments passed to job function.
            **kwargs: Keyword arguments passed to job function.
        """
        with self._lock:
            if job_name in self._scheduled_threads:
                logger.warning("Interval job '%s' is already scheduled. Ignoring duplicate request.", job_name)
                return

            self._is_running = True

        def _interval_loop() -> None:
            logger.info(
                "Interval job '%s' scheduled to run every %.1f seconds (run_immediately=%s)",
                job_name,
                interval_seconds,
                run_immediately,
            )
            if run_immediately:
                try:
                    logger.info("Executing initial run for interval job: %s", job_name)
                    job_func(*args, **kwargs)
                except Exception as err:
                    logger.error("Error in initial run of interval job '%s': %s", job_name, err, exc_info=True)

            while True:
                slept = 0.0
                while slept < interval_seconds:
                    with self._lock:
                        if not self._is_running:
                            return
                    chunk = min(0.5, interval_seconds - slept)
                    time.sleep(chunk)
                    slept += chunk

                with self._lock:
                    should_run = self._is_running

                if should_run:
                    try:
                        logger.debug("Executing scheduled interval job: %s", job_name)
                        job_func(*args, **kwargs)
                    except Exception as err:
                        logger.error("Error executing interval job '%s': %s", job_name, err, exc_info=True)

        with self._lock:
            thread = threading.Thread(target=_interval_loop, name=f"scheduler-interval-{job_name}", daemon=True)
            self._scheduled_threads[job_name] = thread
            thread.start()

    def schedule_market_hours_sync(
        self,
        engine: Any,
        execution_times: Optional[List[str]] = None,
        check_trading_day: bool = True,
        dry_run: bool = False,
    ) -> List[str]:
        """
        Schedules automated market-hours synchronization across BSE, NSE, and GMP.
        Defaults to 09:15 Market Open, 13:00 Mid-Day, 17:00 Market Close IST.

        Args:
            engine: SQLAlchemy Engine instance.
            execution_times: List of HH:MM IST strings (defaults to ["09:15", "13:00", "17:00"]).
            check_trading_day: Enforce Monday-Friday trading calendar guard.
            dry_run: Whether to simulate updates without persisting.

        Returns:
            List of registered job names.
        """
        from ipo_platform.jobs.live_sync_job import DEFAULT_MARKET_HOURS_SLOTS, run_live_market_sync_job

        slots = execution_times or DEFAULT_MARKET_HOURS_SLOTS
        registered = []

        for slot_time in slots:
            slot_clean = slot_time.strip()
            job_name = f"market_sync_{slot_clean.replace(':', '')}"

            def _create_slot_runner(j_name: str):
                return lambda: run_live_market_sync_job(
                    engine=engine,
                    dry_run=dry_run,
                    job_name=j_name,
                    check_trading_day=check_trading_day,
                    tz=self.tz,
                )

            self.schedule_daily_job(
                job_name=job_name,
                job_func=_create_slot_runner(job_name),
                execution_time=slot_clean,
            )
            registered.append(job_name)

        logger.info("Market hours synchronization scheduled for IST slots: %s", registered)
        return registered

    def stop_all(self) -> None:
        """Stops all scheduled background job scheduler threads safely."""
        with self._lock:
            if not self._is_running:
                return
            logger.info("Stopping all scheduled job threads...")
            self._is_running = False
            threads_to_join = list(self._scheduled_threads.values())
            self._scheduled_threads.clear()

        for thread in threads_to_join:
            thread.join(timeout=2.0)
        logger.info("All scheduled job threads stopped.")
