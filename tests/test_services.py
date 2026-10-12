"""
Unit Tests for Application Service Layer (IPOIngestionService, IPOQueryService, IPOBacktestService).
Verifies service facades over repositories and database session operations.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.db import get_engine, init_db
from ipo_platform.models.enums import IPOStatusEnum
from ipo_platform.models.schema import GMPData, HistoricalIPO, PerformanceEvent
from ipo_platform.services import (
    IPOBacktestService,
    IPOIngestionService,
    IPOQueryService,
)


class TestApplicationServices(unittest.TestCase):
    def setUp(self):
        """Initializes isolated test database for service tests."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

        self.ingestion_service = IPOIngestionService(self.engine)
        self.query_service = IPOQueryService(self.engine)
        self.backtest_service = IPOBacktestService(self.engine)

        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "TEST-MB-SERV-001",
                "company_name": "Service Facade Ltd",
                "company_legal_name": "Service Facade Private Limited",
                "ticker_symbol": "SERVFAC",
                "isin": "INE005S01015",
                "segment": "Mainboard",
                "sector": "Cloud Computing",
                "industry": "SaaS",
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
                "issue_size": {"value": 750.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 500.0, "unit": "Crores"},
                "ofs_amount": {"value": 250.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 66.67},
                "ofs_percentage": {"value": 33.33},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 300.0},
                "price_band_high": {"value": 315.0},
                "issue_price": {"value": 315.0},
                "lot_size": {"value": 47},
                "minimum_investment": {"value": 14805.0},
            },
            "valuation_data": {
                "reference_price": 315.0,
                "reference_eps": 12.0,
                "issue_pe": {"value": 26.25},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 315.0,
                "target_price": 441.0,
                "required_price_movement": 40.0,
                "target_pe": 36.75,
                "supporting_factors": ["High SaaS ARR growth"],
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

    def test_ingestion_and_query_services(self):
        # 1. Ingest via service
        record = self.ingestion_service.ingest_json_dict(self.sample_json)
        self.assertEqual(record.ipo_entity.ipo_id, "TEST-MB-SERV-001")

        # 2. Query via service
        fetched = self.query_service.get_ipo_details("TEST-MB-SERV-001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.ipo_entity.company_name, "Service Facade Ltd")

        # 3. Query by slug
        fetched_slug = self.query_service.get_ipo_by_slug("SERVFAC")
        self.assertIsNotNone(fetched_slug)
        self.assertEqual(fetched_slug.ipo_entity.ipo_id, "TEST-MB-SERV-001")

        # 4. List active IPOs
        all_ipos = self.query_service.list_active_ipos()
        self.assertEqual(len(all_ipos), 1)

        # 5. List by status
        upcoming_ipos = self.query_service.list_ipos_by_status(IPOStatusEnum.UPCOMING)
        self.assertEqual(len(upcoming_ipos), 1)

    def test_gmp_quote_service_facade(self):
        gmp_data = GMPData(
            gmp_value=60.0,
            gmp_percentage=19.05,
            gmp_date="2026-09-26",
            gmp_time="12:00:00",
            reference_price=315.0,
            implied_price=375.0,
            source="Market Tracker",
        )

        self.ingestion_service.record_gmp_quote("TEST-MB-SERV-001", gmp_data)
        latest_gmp = self.query_service.get_latest_gmp_quote("TEST-MB-SERV-001")
        self.assertIsNotNone(latest_gmp)
        self.assertEqual(latest_gmp.gmp_value, 60.0)

    def test_backtest_service_facade(self):
        self.ingestion_service.ingest_json_dict(self.sample_json)

        hist_data = HistoricalIPO(
            historical_ipo=True,
            ipo_year=2026,
            listing_price=360.0,
            listing_day_close=380.0,
            listing_day_return=20.63,
        )

        saved_hist = self.backtest_service.record_historical_outcome("TEST-MB-SERV-001", hist_data)
        self.assertEqual(saved_hist.listing_day_return, 20.63)

        fetched_hist = self.backtest_service.get_historical_outcome("TEST-MB-SERV-001")
        self.assertIsNotNone(fetched_hist)
        self.assertEqual(fetched_hist.listing_day_return, 20.63)

        event = PerformanceEvent(
            event_date="2026-10-05",
            event_type="Listing",
            reference_price=315.0,
            market_price=380.0,
            return_percentage=20.63,
            days_from_listing=0,
            reached_40_percent_target=False,
            source="NSE",
        )
        self.backtest_service.record_price_event("TEST-MB-SERV-001", event)

        events = self.backtest_service.list_price_events("TEST-MB-SERV-001")
        self.assertEqual(len(events), 1)

        sim_results = self.backtest_service.run_backtest_simulation(["TEST-MB-SERV-001"])
        self.assertIn("win_rate_percent", sim_results)


if __name__ == "__main__":
    unittest.main()
