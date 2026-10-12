"""
Unit Tests for Platform Observability (Structured Logging, Context Propagation, and Metrics).
Verifies JSON formatting, correlation ID propagation, secrets redaction, and in-memory metrics.
"""

import io
import json
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ipo_platform.observability.logging import (
    LogContextManager,
    StructuredJSONFormatter,
    clear_context,
    get_correlation_id,
    get_ipo_context,
    log_exception,
    redact_secrets,
    set_correlation_id,
    set_ipo_context,
    setup_logging,
)
from ipo_platform.observability.metrics import (
    Counter,
    Gauge,
    MetricsRegistry,
    Timer,
)


class TestObservabilityLogging(unittest.TestCase):
    def setUp(self):
        clear_context()

    def tearDown(self):
        clear_context()

    def test_structured_json_formatter_standard_fields(self):
        formatter = StructuredJSONFormatter(redact=True)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg="Processing test IPO %s",
            args=("TECHDYN",),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["logger"], "test_logger")
        self.assertEqual(data["message"], "Processing test IPO TECHDYN")
        self.assertIn("timestamp", data)
        self.assertIsNone(data["correlation_id"])
        self.assertIsNone(data["ipo_id"])

    def test_correlation_and_ipo_context_propagation(self):
        formatter = StructuredJSONFormatter(redact=True)

        set_correlation_id("REQ-998877")
        set_ipo_context("NSE-TECHDYN-2026")

        record = logging.LogRecord(
            name="ingestion_service",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Parsed valuation ratio",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        self.assertEqual(data["correlation_id"], "REQ-998877")
        self.assertEqual(data["ipo_id"], "NSE-TECHDYN-2026")

    def test_log_context_manager_scope(self):
        self.assertIsNone(get_correlation_id())
        self.assertIsNone(get_ipo_context())

        with LogContextManager(correlation_id="CORR-1", ipo_id="IPO-1"):
            self.assertEqual(get_correlation_id(), "CORR-1")
            self.assertEqual(get_ipo_context(), "IPO-1")

        self.assertIsNone(get_correlation_id())
        self.assertIsNone(get_ipo_context())

    def test_secrets_redaction(self):
        formatter = StructuredJSONFormatter(redact=True)
        record = logging.LogRecord(
            name="auth_service",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Connecting to database",
            args=(),
            exc_info=None,
        )
        record.extra_payload = {
            "api_key": "secret_live_key_9999",
            "db_url": "mysql+pymysql://admin:super_secret_password@db.prod.internal/ipo_db",
            "nested": {
                "auth_token": "bearer_xyz_123",
                "safe_field": "public_data",
            },
        }

        output = formatter.format(record)
        data = json.loads(output)

        extra = data["extra"]["extra_payload"]
        self.assertEqual(extra["api_key"], "***REDACTED***")
        self.assertIn("admin:***REDACTED***@db.prod.internal", extra["db_url"])
        self.assertEqual(extra["nested"]["auth_token"], "***REDACTED***")
        self.assertEqual(extra["nested"]["safe_field"], "public_data")

    def test_exception_logging_helper(self):
        stream = io.StringIO()
        logger = logging.getLogger("test_exc_logger")
        logger.setLevel(logging.ERROR)
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredJSONFormatter(redact=True))
        logger.addHandler(handler)

        try:
            raise ValueError("Invalid P/E multiple calculation")
        except ValueError as err:
            log_exception(logger, err, message="Calculation error", extra={"metric": "PE"})

        output = stream.getvalue().strip()
        data = json.loads(output)

        self.assertEqual(data["level"], "ERROR")
        self.assertEqual(data["message"], "Calculation error")
        self.assertEqual(data["exception"]["type"], "ValueError")
        self.assertIn("Invalid P/E multiple calculation", data["exception"]["message"])
        self.assertEqual(data["extra"]["metric"], "PE")


class TestObservabilityMetrics(unittest.TestCase):
    def setUp(self):
        self.registry = MetricsRegistry()

    def test_counter_increments_and_tags(self):
        counter = self.registry.counter("ipo_ingestions_total", "Count of ingested IPOs")

        counter.inc(tags={"source": "nse"})
        counter.inc(2.0, tags={"source": "nse"})
        counter.inc(1.0, tags={"source": "bse"})

        self.assertEqual(counter.get(tags={"source": "nse"}), 3.0)
        self.assertEqual(counter.get(tags={"source": "bse"}), 1.0)
        self.assertEqual(counter.get(tags={"source": "unknown"}), 0.0)

        with self.assertRaises(ValueError):
            counter.inc(-1.0)

    def test_gauge_set_and_tags(self):
        gauge = self.registry.gauge("active_jobs", "Currently running briefing jobs")
        gauge.set(5.0)
        self.assertEqual(gauge.get(), 5.0)

        gauge.set(2.0, tags={"worker": "node-1"})
        self.assertEqual(gauge.get(tags={"worker": "node-1"}), 2.0)

    def test_timer_observations_and_percentiles(self):
        timer = self.registry.timer("adapter_fetch_latency_seconds", "Adapter fetch latency")

        for latency in [0.010, 0.020, 0.030, 0.040, 0.100]:
            timer.observe(latency, tags={"adapter": "nse"})

        stats = timer.stats(tags={"adapter": "nse"})
        self.assertEqual(stats["count"], 5)
        self.assertAlmostEqual(stats["total_seconds"], 0.200, places=3)
        self.assertAlmostEqual(stats["mean_seconds"], 0.040, places=3)
        self.assertAlmostEqual(stats["min_seconds"], 0.010, places=3)
        self.assertAlmostEqual(stats["max_seconds"], 0.100, places=3)
        self.assertEqual(stats["p50_seconds"], 0.030)

    def test_timer_context_manager_and_decorator(self):
        timer = self.registry.timer("fn_latency")

        with timer.time(tags={"env": "test"}):
            x = 1 + 1

        @timer.wrap(tags={"env": "decorator"})
        def sample_func():
            return 42

        self.assertEqual(sample_func(), 42)

        stats_ctx = timer.stats(tags={"env": "test"})
        stats_dec = timer.stats(tags={"env": "decorator"})
        self.assertEqual(stats_ctx["count"], 1)
        self.assertEqual(stats_dec["count"], 1)

    def test_registry_snapshot(self):
        c = self.registry.counter("req_count")
        c.inc(10)
        g = self.registry.gauge("memory_mb")
        g.set(256)

        snap = self.registry.snapshot()
        self.assertIn("timestamp", snap)
        self.assertEqual(len(snap["counters"]), 1)
        self.assertEqual(len(snap["gauges"]), 1)
        self.assertEqual(snap["counters"][0]["name"], "req_count")


if __name__ == "__main__":
    unittest.main()
