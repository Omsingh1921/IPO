"""
Unit Tests for Database Transaction Atomicity & Rollback Guarantees.
Verifies complete session rollback on forced multi-table save failures and integrity violations.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func
from ipo_platform.db import (
    IPOMasterModel,
    ObjectOfIssueModel,
    FinancialModel,
    ValuationModel,
    IPOWriteRepository,
    DuplicateIPOSlugError,
    ConstraintViolationError,
    get_db_session,
    get_engine,
    init_db,
)
from ipo_platform.io.json_ingestor import JSONIngestor


class TestDBRollback(unittest.TestCase):
    def setUp(self):
        """Initializes isolated in-memory test database for transaction rollback tests."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "TEST-MB-ROLL-001",
                "company_name": "Rollback Corp Ltd",
                "company_legal_name": "Rollback Corp Private Limited",
                "ticker_symbol": "ROLLCORP",
                "isin": "INE003R01015",
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
                "issue_size": {"value": 600.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 400.0, "unit": "Crores"},
                "ofs_amount": {"value": 200.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 66.67},
                "ofs_percentage": {"value": 33.33},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 100.0},
                "price_band_high": {"value": 110.0},
                "issue_price": {"value": 110.0},
                "lot_size": {"value": 130},
                "minimum_investment": {"value": 14300.0},
            },
            "valuation_data": {
                "reference_price": 110.0,
                "reference_eps": 4.0,
                "issue_pe": {"value": 27.5},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 110.0,
                "target_price": 154.0,
                "required_price_movement": 40.0,
                "target_pe": 38.5,
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

    def test_forced_failure_during_multi_table_save_rolls_back_completely(self):
        """Forces an exception inside get_db_session and verifies 0 orphan rows across all tables."""
        record = JSONIngestor.from_dict(self.sample_json)

        try:
            with get_db_session(self.engine) as session:
                # 1. Save master record
                IPOWriteRepository.save_master_record(session, record)

                # 2. Add an invalid child record missing mandatory NOT NULL field (purpose_description)
                invalid_object = ObjectOfIssueModel(
                    ipo_id="TEST-MB-ROLL-001",
                    purpose_type="General",
                    purpose_description=None,  # NOT NULL constraint violation!
                    amount=100.0,
                )
                session.add(invalid_object)
                session.flush()  # Forces immediate DB flush and error trigger
        except Exception:
            pass  # Exception expected and caught by context manager rollback

        # Verify DB state: total rows across master and child tables MUST be 0!
        with get_db_session(self.engine) as check_session:
            master_count = check_session.execute(select(func.count(IPOMasterModel.id))).scalar()
            objects_count = check_session.execute(select(func.count(ObjectOfIssueModel.id))).scalar()
            financials_count = check_session.execute(select(func.count(FinancialModel.id))).scalar()
            valuation_count = check_session.execute(select(func.count(ValuationModel.id))).scalar()

            self.assertEqual(master_count, 0)
            self.assertEqual(objects_count, 0)
            self.assertEqual(financials_count, 0)
            self.assertEqual(valuation_count, 0)

    def test_duplicate_key_integrity_error_rollback(self):
        """Verifies duplicate unique key insert raises DuplicateIPOSlugError/ConstraintViolationError and rolls back clean."""
        record1 = JSONIngestor.from_dict(self.sample_json)

        with get_db_session(self.engine) as session:
            IPOWriteRepository.save_master_record(session, record1)

        # Attempt to insert second record with NEW ipo_id but duplicate unique ISIN
        sample_json_dup = dict(self.sample_json)
        sample_json_dup["ipo_entity"] = dict(self.sample_json["ipo_entity"])
        sample_json_dup["ipo_entity"]["ipo_id"] = "TEST-MB-ROLL-002"
        # retains identical isin: "INE003R01015"

        record2 = JSONIngestor.from_dict(sample_json_dup)

        with self.assertRaises((DuplicateIPOSlugError, ConstraintViolationError)):
            with get_db_session(self.engine) as session:
                IPOWriteRepository.save_master_record(session, record2)

        # Verify database still contains exactly 1 record
        with get_db_session(self.engine) as check_session:
            master_count = check_session.execute(select(func.count(IPOMasterModel.id))).scalar()
            self.assertEqual(master_count, 1)


if __name__ == "__main__":
    unittest.main()
