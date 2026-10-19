"""
Unit tests for LiveMarketClient and live adapter scraping integration.
"""

import unittest
from unittest.mock import MagicMock, patch

from ipo_platform.adapters.bse_adapter import BSEAdapter
from ipo_platform.adapters.gmp_adapter import GMPAdapter
from ipo_platform.adapters.live_market_client import LiveMarketClient
from ipo_platform.adapters.nse_adapter import NSEAdapter


class TestLiveMarketClient(unittest.TestCase):
    """Test suite validating live market client request parsing and adapter wiring."""

    def setUp(self):
        self.client = LiveMarketClient(timeout_seconds=2.0)

    def test_header_generation_and_cookie_jar(self):
        headers = self.client._get_headers(referer="https://example.com")
        self.assertIn("User-Agent", headers)
        self.assertEqual(headers["Referer"], "https://example.com")

        # Test cookie updates
        class MockHeaders:
            @staticmethod
            def get_all(name, default):
                return ["nsit=session123; Path=/; Domain=.nseindia.com"]

        self.client._update_cookies(MockHeaders())
        headers_with_cookie = self.client._get_headers()
        self.assertIn("Cookie", headers_with_cookie)
        self.assertIn("nsit=session123", headers_with_cookie["Cookie"])

    def test_nse_adapter_offline_fallback(self):
        adapter = NSEAdapter(live=False)
        items = adapter.fetch(limit=5)
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 0)

    def test_bse_adapter_offline_fallback(self):
        adapter = BSEAdapter(live=False)
        items = adapter.fetch(limit=5)
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 0)

    def test_gmp_adapter_offline_fallback(self):
        adapter = GMPAdapter(live=False)
        items = adapter.fetch(limit=5)
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 0)


if __name__ == "__main__":
    unittest.main()
