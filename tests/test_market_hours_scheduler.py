"""
Unit Tests for Phase 1 (Market Hours Auto-Scheduler) & Phase 2 (Live Feeds Health Badges).
Verifies:
1. Trading day calendar logic (Mon-Fri active, Sat-Sun skipped).
2. Live market sync job runner state persistence in scheduled_job_executions.
3. JobScheduler and DistributedJobScheduler 3-slot registration (09:15, 13:00, 17:00 IST).
4. GET /scheduler/history and POST /scheduler/trigger-sync API endpoints.
5. GET /health/feeds upstream latency probing and caching.
"""

from datetime import date, datetime, timedelta, timezone
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient

from ipo_platform.api.app import create_app
from ipo_platform.db import get_engine, init_db
from ipo_platform.db.session import get_db_session
from ipo_platform.jobs.distributed_scheduler import DistributedJobScheduler
from ipo_platform.jobs.execution_history import (
    JobExecutionHistoryRepository,
    JobExecutionStatus,
)
from ipo_platform.jobs.live_sync_job import (
    DEFAULT_MARKET_HOURS_SLOTS,
    IST_TIMEZONE,
    is_market_trading_day,
    run_live_market_sync_job,
)
from ipo_platform.jobs.scheduler import JobScheduler


class TestMarketHoursSchedulerAndFeedHealth(unittest.TestCase):
    def setUp(self):
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)
        from ipo_platform.api.dependencies import set_db_engine
        set_db_engine(self.engine)

        from ipo_platform.security import Role, create_access_token
        admin_token = create_access_token(principal_id="test-admin", role=Role.ADMIN)
        self.app = create_app()
        self.auth_headers = {"Authorization": f"Bearer {admin_token}"}
        self.client = TestClient(self.app, headers=self.auth_headers)

    def tearDown(self):
        from ipo_platform.api.dependencies import set_db_engine
        set_db_engine(None)
        self.engine.dispose()

    def test_is_market_trading_day(self):
        """Verifies weekday trading day calculation (Monday-Friday True, Sat-Sun False)."""
        monday = date(2026, 10, 19)    # Mon
        friday = date(2026, 10, 23)    # Fri
        saturday = date(2026, 10, 24)  # Sat
        sunday = date(2026, 10, 25)    # Sun

        self.assertTrue(is_market_trading_day(monday))
        self.assertTrue(is_market_trading_day(friday))
        self.assertFalse(is_market_trading_day(saturday))
        self.assertFalse(is_market_trading_day(sunday))

    def test_run_live_market_sync_job_weekday_execution(self):
        """Tests live market sync execution on a weekday records STARTED and COMPLETED in database."""
        target_date = date(2026, 10, 19)  # Monday

        mock_sync_summary = MagicMock()
        mock_sync_summary.master_records_ingested = 5
        mock_sync_summary.gmp_quotes_recorded = 12
        mock_sync_summary.errors = []

        with patch("ipo_platform.jobs.live_sync_job.datetime") as mock_dt, \
             patch("ipo_platform.jobs.live_sync_job.SourceSyncService") as mock_service_cls:
            mock_now = datetime(2026, 10, 19, 9, 15, 0, tzinfo=IST_TIMEZONE)
            mock_dt.now.return_value = mock_now
            mock_service = mock_service_cls.return_value
            mock_service.sync_all.return_value = mock_sync_summary

            res = run_live_market_sync_job(
                engine=self.engine,
                dry_run=True,
                job_name="market_sync_0915",
                check_trading_day=True,
                node_id="test-node-1",
            )

            self.assertEqual(res["status"], JobExecutionStatus.COMPLETED.value)
            self.assertEqual(res["master_records_ingested"], 5)
            self.assertEqual(res["gmp_quotes_recorded"], 12)

            # Verify persisted in database
            with get_db_session(self.engine) as session:
                rec = JobExecutionHistoryRepository.get_execution(session, "market_sync_0915", target_date)
                self.assertIsNotNone(rec)
                self.assertEqual(rec.execution_status, JobExecutionStatus.COMPLETED.value)
                self.assertIsNotNone(rec.completed_at)

    def test_run_live_market_sync_job_weekend_skipped(self):
        """Tests live market sync execution on a weekend is SKIPPED with audit trail."""
        target_date = date(2026, 10, 24)  # Saturday

        with patch("ipo_platform.jobs.live_sync_job.datetime") as mock_dt:
            mock_now = datetime(2026, 10, 24, 13, 0, 0, tzinfo=IST_TIMEZONE)
            mock_dt.now.return_value = mock_now

            res = run_live_market_sync_job(
                engine=self.engine,
                dry_run=True,
                job_name="market_sync_1300",
                check_trading_day=True,
                node_id="test-node-1",
            )

            self.assertEqual(res["status"], JobExecutionStatus.SKIPPED.value)
            self.assertIn("Non-trading day", res["reason"])

            with get_db_session(self.engine) as session:
                rec = JobExecutionHistoryRepository.get_execution(session, "market_sync_1300", target_date)
                self.assertIsNotNone(rec)
                self.assertEqual(rec.execution_status, JobExecutionStatus.SKIPPED.value)

    def test_scheduler_market_hours_slots_registration(self):
        """Tests that JobScheduler registers the 3 market hours slots."""
        scheduler = JobScheduler()
        try:
            registered = scheduler.schedule_market_hours_sync(
                engine=self.engine,
                execution_times=["09:15", "13:00", "17:00"],
                check_trading_day=True,
            )
            self.assertEqual(len(registered), 3)
            self.assertIn("market_sync_0915", registered)
            self.assertIn("market_sync_1300", registered)
            self.assertIn("market_sync_1700", registered)

            scheduled_jobs = scheduler.get_scheduled_jobs()
            for slot in registered:
                self.assertIn(slot, scheduled_jobs)
        finally:
            scheduler.stop_all()

    def test_distributed_scheduler_market_hours_registration(self):
        """Tests that DistributedJobScheduler registers the 3 market hours slots."""
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        scheduler = DistributedJobScheduler(self.engine, lock_factory=lambda n: mock_lock)
        try:
            registered = scheduler.schedule_market_hours_sync(
                execution_times=["09:15", "13:00", "17:00"],
                check_trading_day=True,
            )
            self.assertEqual(len(registered), 3)
            self.assertIn("market_sync_0915", registered)
            self.assertIn("market_sync_1300", registered)
            self.assertIn("market_sync_1700", registered)
        finally:
            scheduler.stop_all()

    def test_api_scheduler_endpoints(self):
        """Tests GET /scheduler/history and POST /scheduler/trigger-sync."""
        # 1. Initial history
        resp = self.client.get("/scheduler/history", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("executions", data)

        # 2. Trigger on-demand sync (dry_run=True, force_weekend=True)
        resp_trig = self.client.post("/scheduler/trigger-sync?dry_run=true&force_weekend=true", headers=self.auth_headers)
        self.assertEqual(resp_trig.status_code, 200)
        trig_data = resp_trig.json()
        self.assertEqual(trig_data["status"], "COMPLETED")
        self.assertGreaterEqual(trig_data["duration_seconds"], 0.0)

        # 3. Verify history now has the record
        resp_after = self.client.get("/scheduler/history", headers=self.auth_headers)
        self.assertEqual(resp_after.status_code, 200)
        self.assertGreaterEqual(resp_after.json()["total"], 1)

    def test_api_health_feeds_endpoint(self):
        """Tests GET /health/feeds returns real-time ping latencies for BSE, NSE, and GMP."""
        resp = self.client.get("/health/feeds")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("overall_status", data)
        self.assertIn("total_probe_duration_ms", data)
        self.assertIn("feeds", data)

        feeds = data["feeds"]
        self.assertIn("bse", feeds)
        self.assertIn("nse", feeds)
        self.assertIn("gmp", feeds)

        for feed_key in ("bse", "nse", "gmp"):
            feed = feeds[feed_key]
            self.assertIn(feed["status"], ("healthy", "degraded", "unhealthy"))
            self.assertGreaterEqual(feed["latency_ms"], 0.0)
            self.assertIn("last_check", feed)


if __name__ == "__main__":
    unittest.main()
