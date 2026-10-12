"""
Unit Tests for Database Concurrency & Optimistic Concurrency Control (OCC).
Verifies version_id incrementing, expected_version mismatch enforcement, and StaleDataError handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from ipo_platform.db import (
    IPOMasterModel,
    IPOWriteRepository,
    OptimisticLockError,
    get_db_session,
    get_engine,
    init_db,
)
from ipo_platform.io.json_ingestor import JSONIngestor
from ipo_platform.models.enums import IPOStatusEnum


class TestDBConcurrency(unittest.TestCase):
    def setUp(self):
        """Initializes isolated test database for concurrency tests."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "TEST-MB-CONC-001",
                "company_name": "Concurrency Corp Ltd",
                "company_legal_name": "Concurrency Corp Limited",
                "ticker_symbol": "CONCCORP",
                "isin": "INE002C01015",
                "segment": "Mainboard",
                "sector": "Fintech",
                "industry": "Payments",
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
                "issue_size": {"value": 800.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 500.0, "unit": "Crores"},
                "ofs_amount": {"value": 300.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 62.5},
                "ofs_percentage": {"value": 37.5},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 150.0},
                "price_band_high": {"value": 160.0},
                "issue_price": {"value": 160.0},
                "lot_size": {"value": 90},
                "minimum_investment": {"value": 14400.0},
            },
            "valuation_data": {
                "reference_price": 160.0,
                "reference_eps": 5.0,
                "issue_pe": {"value": 32.0},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 160.0,
                "target_price": 224.0,
                "required_price_movement": 40.0,
                "target_pe": 44.8,
                "supporting_factors": [],
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

    def test_version_id_increments_on_update(self):
        record = JSONIngestor.from_dict(self.sample_json)

        # 1. Initial save sets version_id = 1
        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        with get_db_session(self.engine) as session:
            master = session.execute(
                select(IPOMasterModel).where(IPOMasterModel.ipo_id == "TEST-MB-CONC-001")
            ).scalars().first()
            self.assertEqual(master.version_id, 1)

        # 2. Update record increments version_id to 2
        record.ipo_entity.company_name = "Concurrency Corp Updated Ltd"
        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        with get_db_session(self.engine) as session:
            master = session.execute(
                select(IPOMasterModel).where(IPOMasterModel.ipo_id == "TEST-MB-CONC-001")
            ).scalars().first()
            self.assertEqual(master.version_id, 2)

    def test_update_status_version_mismatch_raises_optimistic_lock_error(self):
        record = JSONIngestor.from_dict(self.sample_json)

        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        # Attempt to update with incorrect expected_version (e.g. 5 instead of 1)
        with self.assertRaises(OptimisticLockError):
            with get_db_session(self.engine) as session:
                IPOWriteRepository.update_status(
                    session, "TEST-MB-CONC-001", IPOStatusEnum.CURRENTLY_OPEN, expected_version=5
                )

    def test_soft_delete_version_mismatch_raises_optimistic_lock_error(self):
        record = JSONIngestor.from_dict(self.sample_json)

        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        # Attempt soft delete with stale expected_version
        with self.assertRaises(OptimisticLockError):
            with get_db_session(self.engine) as session:
                IPOWriteRepository.soft_delete(session, "TEST-MB-CONC-001", expected_version=99)

    def test_concurrent_update_collision_protection(self):
        record = JSONIngestor.from_dict(self.sample_json)

        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record)

        # Simulate session A updating status from version 1 -> 2
        with get_db_session(self.engine) as session_a:
            IPOWriteRepository.update_status(session_a, "TEST-MB-CONC-001", IPOStatusEnum.CURRENTLY_OPEN, expected_version=1)

        # Session B attempts update assuming expected_version is still 1 -> Collision!
        with self.assertRaises(OptimisticLockError):
            with get_db_session(self.engine) as session_b:
                IPOWriteRepository.update_status(session_b, "TEST-MB-CONC-001", IPOStatusEnum.CLOSED, expected_version=1)


if __name__ == "__main__":
    unittest.main()
