"""
Unit Tests for Subsystem Health Checks and Diagnostic Aggregator.
Verifies database, redis, adapter, notification probes, failure isolation, and report generation.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ipo_platform.db import get_engine, init_db
from ipo_platform.observability.health import (
    HealthAggregator,
    HealthCheckResult,
    HealthStatus,
    SystemHealthReport,
    check_adapters,
    check_database,
    check_notifications,
    check_redis,
)


class TestHealthChecksAndAggregator(unittest.TestCase):
    def setUp(self):
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_database_health_check_healthy(self):
        result = check_database(self.engine)
        self.assertEqual(result.name, "database")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertTrue(result.is_healthy)
        self.assertGreaterEqual(result.duration_ms, 0.0)

    def test_database_health_check_unhealthy(self):
        broken_engine = get_engine("sqlite:///:memory:")
        broken_engine.dispose()

        # Mock connect to raise an error
        broken_mock = MagicMock()
        broken_mock.connect.side_effect = ConnectionError("Could not connect to database host")
        broken_mock.dialect.name = "postgresql"

        result = check_database(broken_mock)
        self.assertEqual(result.name, "database")
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertFalse(result.is_healthy)
        self.assertIn("Could not connect", result.message)

    def test_redis_health_check(self):
        # Unconfigured Redis -> DEGRADED
        result_unconfigured = check_redis(None)
        self.assertEqual(result_unconfigured.status, HealthStatus.DEGRADED)

        # Configured Redis with successful ping -> HEALTHY
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        result_healthy = check_redis(mock_redis)
        self.assertEqual(result_healthy.status, HealthStatus.HEALTHY)

        # Configured Redis with ping raising exception -> UNHEALTHY
        mock_redis_fail = MagicMock()
        mock_redis_fail.ping.side_effect = TimeoutError("Redis host unreachable")
        result_fail = check_redis(mock_redis_fail)
        self.assertEqual(result_fail.status, HealthStatus.UNHEALTHY)

    def test_adapter_health_check(self):
        # All healthy adapters
        mock_mgr_healthy = MagicMock()
        mock_mgr_healthy.health_check_all.return_value = {
            "NSE": True,
            "BSE": True,
            "GMP": True,
        }
        res_healthy = check_adapters(mock_mgr_healthy)
        self.assertEqual(res_healthy.status, HealthStatus.HEALTHY)

        # Partially degraded adapters (1 failed)
        mock_mgr_partial = MagicMock()
        mock_mgr_partial.health_check_all.return_value = {
            "NSE": True,
            "BSE": False,
            "GMP": True,
        }
        res_partial = check_adapters(mock_mgr_partial)
        self.assertEqual(res_partial.status, HealthStatus.DEGRADED)
        self.assertIn("BSE", res_partial.details["failed"])

        # All adapters failed -> UNHEALTHY
        mock_mgr_all_fail = MagicMock()
        mock_mgr_all_fail.health_check_all.return_value = {
            "NSE": False,
            "BSE": False,
        }
        res_fail = check_adapters(mock_mgr_all_fail)
        self.assertEqual(res_fail.status, HealthStatus.UNHEALTHY)

    def test_notification_health_check(self):
        # Empty dispatcher -> DEGRADED
        mock_disp_empty = MagicMock()
        mock_disp_empty.get_registered_channels.return_value = []
        mock_disp_empty.channels = {}
        res_empty = check_notifications(mock_disp_empty)
        self.assertEqual(res_empty.status, HealthStatus.DEGRADED)

        # Active channels -> HEALTHY
        mock_disp_active = MagicMock()
        mock_disp_active.get_registered_channels.return_value = ["telegram", "email"]
        mock_disp_active.channels = {"telegram": MagicMock(), "email": MagicMock()}
        res_active = check_notifications(mock_disp_active)
        self.assertEqual(res_active.status, HealthStatus.HEALTHY)

    def test_health_aggregator_failure_isolation_never_crashes(self):
        aggregator = HealthAggregator()

        def working_probe():
            return HealthCheckResult("subsystem_a", HealthStatus.HEALTHY)

        def exploding_probe():
            raise RuntimeError("Fatal memory segmentation or hardware bus failure")

        aggregator.register("subsystem_a", working_probe)
        aggregator.register("subsystem_b", exploding_probe)

        # Aggregator must NOT raise exception
        report = aggregator.run_checks()

        self.assertIsInstance(report, SystemHealthReport)
        self.assertEqual(report.healthy_count, 1)
        self.assertEqual(report.unhealthy_count, 1)
        self.assertEqual(report.overall_status, HealthStatus.UNHEALTHY)
        self.assertFalse(report.checks["subsystem_b"].is_healthy)
        self.assertIn("Fatal memory", report.checks["subsystem_b"].message)


if __name__ == "__main__":
    unittest.main()
