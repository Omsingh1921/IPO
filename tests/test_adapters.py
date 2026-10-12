"""
Unit Tests for Upstream Data Source Adapters, Circuit Breaker, and Adapter Manager.
Verifies BaseSourceAdapter contracts (fetch, validate, transform, health_check),
resilience (retry, exponential backoff, circuit breaker), offline mock fallbacks,
AdapterManager orchestration, dry-run simulation, and sync-sources CLI integration.
"""

from datetime import date, datetime
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.adapters.adapter_manager import AdapterManager
from ipo_platform.adapters.base import (
    AdapterSyncResult,
    BaseSourceAdapter,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    TokenBucketRateLimiter,
    execute_with_retry,
)
from ipo_platform.adapters.bse_adapter import BSEAdapter
from ipo_platform.adapters.gmp_adapter import GMPAdapter
from ipo_platform.adapters.nse_adapter import NSEAdapter
from ipo_platform.cli import main
from ipo_platform.db import get_engine, init_db
from ipo_platform.models.schema import GMPData, MasterIPORecord
from ipo_platform.services.sync_service import SourceSyncService


class TestAdaptersAndSync(unittest.TestCase):
    def setUp(self):
        """Initializes test database and mock payloads."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

        self.mock_nse_payload = [
            {
                "symbol": "TECHDYN",
                "companyName": "Tech Dynamics Solutions Ltd",
                "series": "EQ",
                "issueStartDate": "2026-10-15",
                "issueEndDate": "2026-10-18",
                "listingDate": "2026-10-23",
                "minPrice": 320.0,
                "maxPrice": 340.0,
                "minBidQuantity": 44,
                "issueSize": 450.0,
                "qibSubscribed": 12.5,
                "niiSubscribed": 8.0,
                "retailSubscribed": 4.5,
                "empSubscribed": 1.2,
                "totalSubscribed": 8.8,
                "pe": 28.5,
            }
        ]

        self.mock_bse_payload = [
            {
                "Scrip_Id": "GROWTHINF",
                "Security_Name": "Growth Infrastructure Ltd",
                "Segment": "Mainboard",
                "Start_Date": "2026-10-16",
                "End_Date": "2026-10-19",
                "Listing_Date": "2026-10-24",
                "Floor_Price": 180.0,
                "Cap_Price": 190.0,
                "Market_Lot": 75,
                "Issue_Size": 300.0,
                "PE": 20.0,
            }
        ]

        self.mock_gmp_payload = [
            {
                "ipo_id": f"NSE-TECHDYN-{date.today().year}",
                "gmp_value": 85.0,
                "reference_price": 340.0,
                "date": "2026-10-16",
                "time": "11:30:00",
                "source": "Chittorgarh",
            },
            {
                "ipo_id": "OUTLIER-IPO",
                "gmp_value": 1500.0,  # 1500 on 100 is 1500% -> must be rejected (> 150%)
                "reference_price": 100.0,
                "date": "2026-10-16",
                "time": "11:30:00",
            },
        ]

    def tearDown(self):
        self.engine.dispose()

    def test_rate_limiter_acquisition(self):
        limiter = TokenBucketRateLimiter(requests_per_second=10.0, max_tokens=2.0)
        limiter.acquire()
        limiter.acquire()
        self.assertLessEqual(limiter.tokens, 1.0)

    def test_nse_adapter_parsing(self):
        mock_client = MagicMock(return_value=self.mock_nse_payload)
        adapter = NSEAdapter(http_client=mock_client)

        sync_res = adapter.sync()
        self.assertEqual(sync_res.source_name, "NSE")
        self.assertEqual(sync_res.records_fetched, 1)
        self.assertEqual(sync_res.records_valid, 1)
        self.assertEqual(len(sync_res.master_records), 1)

        record: MasterIPORecord = sync_res.master_records[0]
        self.assertEqual(record.ipo_entity.ipo_id, f"NSE-TECHDYN-{date.today().year}")
        self.assertEqual(record.ipo_entity.company_name, "Tech Dynamics Solutions Ltd")
        self.assertEqual(record.issue_structure.price_band_high.value, 340.0)
        self.assertEqual(record.subscription_data["QIB"].subscription_multiple, 12.5)

    def test_bse_adapter_parsing(self):
        mock_client = MagicMock(return_value=self.mock_bse_payload)
        adapter = BSEAdapter(http_client=mock_client)

        sync_res = adapter.sync()
        self.assertEqual(sync_res.source_name, "BSE")
        self.assertEqual(sync_res.records_fetched, 1)
        self.assertEqual(sync_res.records_valid, 1)
        self.assertEqual(len(sync_res.master_records), 1)

        record: MasterIPORecord = sync_res.master_records[0]
        self.assertEqual(record.ipo_entity.ipo_id, f"BSE-GROWTHINF-{date.today().year}")
        self.assertEqual(record.ipo_entity.company_name, "Growth Infrastructure Ltd")
        self.assertEqual(record.issue_structure.price_band_high.value, 190.0)

    def test_gmp_adapter_sanity_and_outlier_filtering(self):
        mock_client = MagicMock(return_value=self.mock_gmp_payload)
        adapter = GMPAdapter(http_client=mock_client)

        sync_res = adapter.sync()
        self.assertEqual(sync_res.source_name, "GMP")
        self.assertEqual(sync_res.records_fetched, 2)
        # Outlier quote (1500%) must be rejected, valid quote accepted
        self.assertEqual(sync_res.records_valid, 1)
        self.assertEqual(len(sync_res.gmp_quotes), 1)

        ipo_id, quote = sync_res.gmp_quotes[0]
        self.assertEqual(ipo_id, f"NSE-TECHDYN-{date.today().year}")
        self.assertEqual(quote.gmp_value, 85.0)
        self.assertEqual(quote.gmp_percentage, 25.0)

    def test_sync_service_dry_run_mode(self):
        nse_adapter = NSEAdapter(http_client=MagicMock(return_value=self.mock_nse_payload))
        bse_adapter = BSEAdapter(http_client=MagicMock(return_value=self.mock_bse_payload))
        gmp_adapter = GMPAdapter(http_client=MagicMock(return_value=self.mock_gmp_payload))

        sync_service = SourceSyncService(
            engine=self.engine,
            adapters=[nse_adapter, bse_adapter, gmp_adapter],
        )

        summary = sync_service.sync_all(dry_run=True)
        self.assertTrue(summary.dry_run)
        self.assertEqual(summary.total_sources, 3)
        self.assertEqual(summary.total_fetched, 4)
        self.assertEqual(summary.total_valid, 3)

    def test_sync_service_live_persistence(self):
        nse_adapter = NSEAdapter(http_client=MagicMock(return_value=self.mock_nse_payload))
        gmp_adapter = GMPAdapter(http_client=MagicMock(return_value=self.mock_gmp_payload))

        sync_service = SourceSyncService(
            engine=self.engine,
            adapters=[nse_adapter, gmp_adapter],
        )

        summary = sync_service.sync_all(sources=["nse", "gmp"], dry_run=False)
        self.assertFalse(summary.dry_run)
        self.assertEqual(summary.master_records_ingested, 1)
        self.assertEqual(summary.gmp_quotes_recorded, 1)
        self.assertEqual(len(summary.errors), 0)

    def test_cli_sync_sources_command(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        db_url = f"sqlite:///{db_path}"
        engine = get_engine(db_url)
        init_db(engine)
        engine.dispose()

        try:
            with patch("sys.stdout") as mock_out:
                code = main([
                    "--db-url", db_url,
                    "sync-sources",
                    "--source", "all",
                    "--dry-run",
                    "--limit", "10",
                ])
                self.assertEqual(code, 0)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

    # --- New Stage 4 Resiliency & Adapter Framework Tests ---

    def test_circuit_breaker_trip_and_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0.2)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)

        def failing_func():
            raise ConnectionError("Upstream timeout")

        # 1st failure
        with self.assertRaises(ConnectionError):
            cb.call(failing_func)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 1)

        # 2nd failure -> trips circuit breaker to OPEN
        with self.assertRaises(ConnectionError):
            cb.call(failing_func)
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        # Call while OPEN must fast-fail with CircuitBreakerOpenError immediately
        with self.assertRaises(CircuitBreakerOpenError):
            cb.call(failing_func)

        # Wait for recovery timeout to transition to HALF_OPEN
        time.sleep(0.25)
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        # Successful probe resets breaker to CLOSED
        def successful_func():
            return "OK"

        result = cb.call(successful_func)
        self.assertEqual(result, "OK")
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_execute_with_retry_and_backoff(self):
        call_count = 0

        def transient_failure():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "SUCCESS"

        result = execute_with_retry(
            transient_failure,
            max_retries=3,
            initial_delay=0.01,
            backoff_factor=1.5,
        )
        self.assertEqual(result, "SUCCESS")
        self.assertEqual(call_count, 3)

    def test_base_source_adapter_contracts(self):
        mock_client = MagicMock(return_value=self.mock_nse_payload)
        adapter = NSEAdapter(http_client=mock_client)

        # Test health_check()
        self.assertTrue(adapter.health_check())
        self.assertTrue(adapter.test_connectivity())

        # Test fetch()
        items = adapter.fetch(limit=10)
        self.assertEqual(len(items), 1)

        # Test validate()
        self.assertTrue(adapter.validate(items[0]))
        self.assertFalse(adapter.validate({}))
        self.assertFalse(adapter.validate({"symbol": "BAD", "minPrice": -10}))

        # Test transform()
        record = adapter.transform(items[0])
        self.assertIsInstance(record, MasterIPORecord)
        self.assertEqual(record.ipo_entity.ticker_symbol, "TECHDYN")

    def test_adapter_manager_orchestration_and_health_checks(self):
        nse_adapter = NSEAdapter(http_client=MagicMock(return_value=self.mock_nse_payload))
        bse_adapter = BSEAdapter(http_client=MagicMock(return_value=self.mock_bse_payload))
        gmp_adapter = GMPAdapter(http_client=MagicMock(return_value=self.mock_gmp_payload))

        manager = AdapterManager(
            engine=self.engine,
            adapters=[nse_adapter, bse_adapter, gmp_adapter],
        )

        # Verify registration & listing
        registered = manager.list_adapters()
        self.assertIn("NSE", registered)
        self.assertIn("BSE", registered)
        self.assertIn("GMP", registered)

        # Verify health check all
        health = manager.health_check_all()
        self.assertTrue(health["NSE"])
        self.assertTrue(health["BSE"])
        self.assertTrue(health["GMP"])

        # Verify orchestration with dry_run
        summary = manager.orchestrate_sync(dry_run=True)
        self.assertTrue(summary.dry_run)
        self.assertEqual(summary.total_sources, 3)
        self.assertEqual(summary.total_fetched, 4)
        self.assertEqual(summary.total_valid, 3)

        # Verify live persistence through AdapterManager
        summary_live = manager.orchestrate_sync(sources=["nse", "gmp"], dry_run=False)
        self.assertFalse(summary_live.dry_run)
        self.assertEqual(summary_live.master_records_ingested, 1)
        self.assertEqual(summary_live.gmp_quotes_recorded, 1)

    def test_offline_deterministic_fallback(self):
        # Without http_client, offline fallback generates valid deterministic records
        adapter = NSEAdapter()
        items = adapter.fetch(limit=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["symbol"], "TECHDYN")
        self.assertTrue(adapter.validate(items[0]))
        record = adapter.transform(items[0])
        self.assertIsInstance(record, MasterIPORecord)


if __name__ == "__main__":
    unittest.main()
