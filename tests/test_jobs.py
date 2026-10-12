"""
Unit Tests for Daily Briefing Service, Job Runners, and Job Scheduler.
Verifies daily briefing generation, Markdown file output, manual job execution, and scheduling.
"""

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.db import get_engine, init_db
from ipo_platform.jobs.daily_briefing_job import run_daily_briefing_job
from ipo_platform.jobs.scheduler import JobScheduler
from ipo_platform.models.schema import GMPData
from ipo_platform.services.briefing_service import DailyBriefingService
from ipo_platform.services.ingestion_service import IPOIngestionService


class TestJobsAndBriefing(unittest.TestCase):
    def setUp(self):
        """Initializes test database and output reports directory."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

        self.test_reports_dir = os.path.join("scratch", "test_reports")
        os.makedirs(self.test_reports_dir, exist_ok=True)

        self.ingestion_service = IPOIngestionService(self.engine)
        self.briefing_service = DailyBriefingService(self.engine, reports_dir=self.test_reports_dir)

        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "TEST-MB-BRIEF-001",
                "company_name": "Briefing Dynamics Ltd",
                "company_legal_name": "Briefing Dynamics Private Limited",
                "ticker_symbol": "BRIEFDYN",
                "isin": "INE006B01015",
                "segment": "Mainboard",
                "sector": "Fintech",
                "industry": "Payments",
            },
            "ipo_status": {
                "status": "Currently Open",
                "research_date": "2026-09-24",
                "research_time": "10:00:00",
                "data_cutoff": "2026-09-24 10:00:00",
                "open_date": "2026-09-24",
                "close_date": "2026-09-26",
                "listing_date": "2026-09-30",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 600.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 400.0, "unit": "Crores"},
                "ofs_amount": {"value": 200.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 66.67},
                "ofs_percentage": {"value": 33.33},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 250.0},
                "price_band_high": {"value": 260.0},
                "issue_price": {"value": 260.0},
                "lot_size": {"value": 57},
                "minimum_investment": {"value": 14820.0},
            },
            "valuation_data": {
                "reference_price": 260.0,
                "reference_eps": 10.0,
                "issue_pe": {"value": 26.0},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 260.0,
                "target_price": 364.0,
                "required_price_movement": 40.0,
                "target_pe": 36.4,
                "supporting_factors": ["High growth"],
                "contradictory_factors": [],
                "scenario_status": "Supported",
                "scenario_methodology": "Standardized non-predictive model",
                "scenario_data_timestamp": "2026-09-24 10:00:00",
            },
            "data_quality": {
                "completeness_status": "Complete",
                "source_verification_status": "Verified",
                "last_verified": "2026-09-24 10:00:00",
            },
        }

    def tearDown(self):
        """Cleans up temporary test reports directory."""
        if os.path.exists(self.test_reports_dir):
            shutil.rmtree(self.test_reports_dir, ignore_errors=True)

    def test_daily_briefing_service_generation(self):
        # 1. Ingest test record
        self.ingestion_service.ingest_json_dict(self.sample_json)

        # 2. Add GMP quote
        gmp = GMPData(gmp_value=40.0, gmp_percentage=15.38, gmp_date="2026-09-24", gmp_time="11:00:00", reference_price=260.0, implied_price=300.0, source="Tracker")
        self.ingestion_service.record_gmp_quote("TEST-MB-BRIEF-001", gmp)

        # 3. Generate briefing report
        report = self.briefing_service.generate_daily_briefing(target_date="2026-09-26")

        # 4. Assert report contents
        self.assertIn("# Daily IPO Intelligence Briefing — 2026-09-26", report)
        self.assertIn("Briefing Dynamics Ltd", report)
        self.assertIn("₹260.00", report)
        self.assertIn("₹364.00", report)
        self.assertIn("₹40.00 (15.4%)", report)

        # 5. Verify file output on disk
        expected_file = os.path.join(self.test_reports_dir, "briefing_2026-09-26.md")
        self.assertTrue(os.path.exists(expected_file))

    def test_run_daily_briefing_job_runner(self):
        self.ingestion_service.ingest_json_dict(self.sample_json)

        report = run_daily_briefing_job(self.engine, target_date="2026-09-26", reports_dir=self.test_reports_dir)
        self.assertIn("Briefing Dynamics Ltd", report)

    def test_job_scheduler_manual_execution(self):
        res = JobScheduler.run_job_now(lambda: "JOB_COMPLETED")
        self.assertEqual(res, "JOB_COMPLETED")

    def test_scheduler_lifecycle_and_safety(self):
        scheduler = JobScheduler()
        self.assertFalse(scheduler.is_running)

        # 1. Schedule a dummy daily job
        call_count = []
        def dummy_job():
            call_count.append(1)

        scheduler.schedule_daily_job("test_briefing", dummy_job, execution_time="23:59")
        self.assertTrue(scheduler.is_running)
        self.assertEqual(scheduler.get_scheduled_jobs(), ["test_briefing"])

        # 2. Duplicate scheduling attempt must be ignored
        scheduler.schedule_daily_job("test_briefing", dummy_job, execution_time="23:59")
        self.assertEqual(len(scheduler.get_scheduled_jobs()), 1)

        # 3. Stop all must terminate safely
        scheduler.stop_all()
        self.assertFalse(scheduler.is_running)
        self.assertEqual(scheduler.get_scheduled_jobs(), [])

    def test_scheduler_job_exception_resilience(self):
        # Verify manual trigger doesn't crash on exception or behaves predictably
        def failing_job():
            raise RuntimeError("Database temporarily unavailable")

        with self.assertRaises(RuntimeError):
            JobScheduler.run_job_now(failing_job)


if __name__ == "__main__":
    unittest.main()

