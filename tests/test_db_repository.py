"""
Unit Tests for Database Repository Layer (IPOReadRepository, IPOWriteRepository, GMPRepository, BacktestRepository).
Verifies CRUD operations, filter queries, GMP snapshots, and backtest history.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.db import (
    BacktestRepository,
    GMPRepository,
    IPOReadRepository,
    IPOWriteRepository,
    get_db_session,
    get_engine,
    init_db,
)
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.enums import IPOStatusEnum, ScenarioStatusEnum
from ipo_platform.models.schema import GMPData, HistoricalIPO, PerformanceEvent


class TestDBRepository(unittest.TestCase):
    def setUp(self):
        """Initializes isolated in-memory SQLite database for each repository test."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "TEST-MB-2026-REPO",
                "company_name": "Repo Solutions Ltd",
                "company_legal_name": "Repo Solutions Private Limited",
                "ticker_symbol": "REPOSOL",
                "isin": "INE001R01015",
                "segment": "Mainboard",
                "sector": "Software Services",
                "industry": "Enterprise Software",
            },
            "ipo_status": {
                "status": "Upcoming",
                "research_date": "2026-09-24",
                "research_time": "10:00:00",
                "data_cutoff": "2026-09-24 10:00:00",
                "open_date": "2026-09-28",
                "close_date": "2026-09-30",
                "listing_date": "2026-10-05",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 500.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 300.0, "unit": "Crores"},
                "ofs_amount": {"value": 200.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 60.0},
                "ofs_percentage": {"value": 40.0},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 200.0},
                "price_band_high": {"value": 210.0},
                "issue_price": {"value": 210.0},
                "lot_size": {"value": 70},
                "minimum_investment": {"value": 14700.0},
            },
            "valuation_data": {
                "reference_price": 210.0,
                "reference_eps": 8.4,
                "issue_pe": {"value": 25.0},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 210.0,
                "target_price": 294.0,
                "required_price_movement": 40.0,
                "target_pe": 35.0,
                "supporting_factors": ["YoY revenue growth"],
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

    def test_save_and_read_ipo_record(self):
        record = JSONIngestor.from_dict(self.sample_json)

        # 1. Save via IPOWriteRepository
        with get_db_session(self.engine) as session:
            saved_record = IPOWriteRepository.save_master_record(session, record)
            self.assertEqual(saved_record.ipo_entity.ipo_id, "TEST-MB-2026-REPO")

        # 2. Read via IPOReadRepository
        with get_db_session(self.engine) as session:
            fetched = IPOReadRepository.get_by_id(session, "TEST-MB-2026-REPO")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.ipo_entity.company_name, "Repo Solutions Ltd")
            self.assertEqual(fetched.ipo_entity.ticker_symbol, "REPOSOL")
            self.assertEqual(fetched.ipo_status.status, IPOStatusEnum.UPCOMING)

    def test_list_all_and_list_by_status(self):
        record = JSONIngestor.from_dict(self.sample_json)
        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        with get_db_session(self.engine) as session:
            all_records = IPOReadRepository.list_all(session, skip=0, limit=10)
            self.assertEqual(len(all_records), 1)

            upcoming_records = IPOReadRepository.list_by_status(session, IPOStatusEnum.UPCOMING)
            self.assertEqual(len(upcoming_records), 1)

            closed_records = IPOReadRepository.list_by_status(session, IPOStatusEnum.CLOSED)
            self.assertEqual(len(closed_records), 0)

    def test_update_status(self):
        record = JSONIngestor.from_dict(self.sample_json)
        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        # Update status to CURRENTLY_OPEN
        with get_db_session(self.engine) as session:
            success = IPOWriteRepository.update_status(session, "TEST-MB-2026-REPO", IPOStatusEnum.CURRENTLY_OPEN)
            self.assertTrue(success)

        # Verify status updated
        with get_db_session(self.engine) as session:
            fetched = IPOReadRepository.get_by_id(session, "TEST-MB-2026-REPO")
            self.assertEqual(fetched.ipo_status.status, IPOStatusEnum.CURRENTLY_OPEN)

    def test_soft_delete(self):
        record = JSONIngestor.from_dict(self.sample_json)
        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        # Soft delete record
        with get_db_session(self.engine) as session:
            deleted = IPOWriteRepository.soft_delete(session, "TEST-MB-2026-REPO")
            self.assertTrue(deleted)

        # Verify get_by_id returns None for soft-deleted record
        with get_db_session(self.engine) as session:
            fetched = IPOReadRepository.get_by_id(session, "TEST-MB-2026-REPO")
            self.assertIsNone(fetched)

    def test_gmp_snapshot_persistence(self):
        gmp_data = GMPData(
            gmp_value=50.0,
            gmp_percentage=23.8,
            gmp_date="2026-09-25",
            gmp_time="11:30:00",
            reference_price=210.0,
            implied_price=260.0,
            source="Grey Market Tracker",
        )

        with get_db_session(self.engine) as session:
            model = GMPRepository.save_gmp_snapshot(session, "TEST-MB-2026-REPO", gmp_data)
            self.assertEqual(model.gmp_value, 50.0)

        with get_db_session(self.engine) as session:
            latest = GMPRepository.get_latest_gmp(session, "TEST-MB-2026-REPO")
            self.assertIsNotNone(latest)
            self.assertEqual(latest.gmp_value, 50.0)
            self.assertEqual(latest.implied_price, 260.0)

    def test_backtest_repository(self):
        hist_data = HistoricalIPO(
            historical_ipo=True,
            ipo_year=2026,
            listing_price=250.0,
            listing_day_close=265.0,
            listing_day_return=26.19,
        )

        with get_db_session(self.engine) as session:
            BacktestRepository.save_historical_performance(session, "TEST-MB-2026-REPO", hist_data)

        with get_db_session(self.engine) as session:
            fetched_hist = BacktestRepository.get_historical_performance(session, "TEST-MB-2026-REPO")
            self.assertIsNotNone(fetched_hist)
            self.assertEqual(fetched_hist.listing_day_return, 26.19)

        event = PerformanceEvent(
            event_date="2026-10-05",
            event_type="Listing Day",
            reference_price=210.0,
            market_price=265.0,
            return_percentage=26.19,
            days_from_listing=0,
            reached_40_percent_target=False,
            source="NSE",
        )

        with get_db_session(self.engine) as session:
            BacktestRepository.save_performance_event(session, "TEST-MB-2026-REPO", event)

        with get_db_session(self.engine) as session:
            events = BacktestRepository.list_performance_events(session, "TEST-MB-2026-REPO")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].return_percentage, 26.19)


if __name__ == "__main__":
    unittest.main()
