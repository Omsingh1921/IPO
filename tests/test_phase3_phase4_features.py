"""
Unit & Integration Tests for Phase 3 (Granular Subscription Popover)
and Phase 4 (Automatic Financials Bridge).
"""

from datetime import date
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ipo_platform.adapters.financials_adapter import FinancialsBridgeAdapter
from ipo_platform.api.app import create_app
from ipo_platform.api.routes.ipos import _to_list_item
from ipo_platform.api.schemas import IPOListItem
from ipo_platform.models.schema import (
    FinancialRecord,
    GMPData,
    IPOEntity,
    IPOStatus,
    IssueStructure,
    MasterIPORecord,
    ProvenanceEnvelope,
    SubscriptionCategory,
)
from ipo_platform.security.auth import create_access_token
from ipo_platform.security.rbac import Role


class TestPhase3GranularSubscription(unittest.TestCase):
    """Tests for Phase 3: Granular Subscription Extraction and Schema Serialization."""

    def test_ipo_list_item_with_granular_subscription(self):
        item = IPOListItem(
            ipo_id="IPO-APEX-2026",
            company_name="Apex Tech Limited",
            subscription_times=28.5,
            subscription_summary="QIB: 45.2x, NII: 22.1x, Retail: 8.5x",
            qib_subscription=45.2,
            nii_subscription=22.1,
            retail_subscription=8.5,
            employee_subscription=2.1,
            subscription_breakdown={
                "QIB": 45.2,
                "NII": 22.1,
                "Retail": 8.5,
                "Employee": 2.1,
                "Total": 28.5,
            },
        )
        data = item.model_dump()
        self.assertEqual(data["qib_subscription"], 45.2)
        self.assertEqual(data["nii_subscription"], 22.1)
        self.assertEqual(data["retail_subscription"], 8.5)
        self.assertEqual(data["employee_subscription"], 2.1)
        self.assertIn("QIB", data["subscription_breakdown"])
        self.assertEqual(data["subscription_breakdown"]["Total"], 28.5)

    def test_to_list_item_extracts_granular_categories(self):
        rec = MagicMock()
        rec.ipo_entity = MagicMock(
            ipo_id="IPO-TEST-2026",
            company_name="Test Robotics Ltd",
            sector="Technology",
            segment="Mainboard",
            ticker_symbol="TESTROBO",
        )
        rec.ipo_status = MagicMock(
            status="Currently Open",
            open_date=date.today().isoformat(),
            close_date=date.today().isoformat(),
            allotment_date=None,
            listing_date=None,
        )
        rec.issue_structure = None
        rec.gmp_data = None
        rec.subscription_data = {
                "QIB": SubscriptionCategory(
                    shares_offered=100000,
                    shares_bid=3200000,
                    subscription_multiple=32.0,
                    source="NSE Live",
                    source_date="2026-10-19",
                    retrieval_timestamp="2026-10-19 10:00:00",
                ),
                "NII": SubscriptionCategory(
                    shares_offered=100000,
                    shares_bid=1500000,
                    subscription_multiple=15.0,
                    source="NSE Live",
                    source_date="2026-10-19",
                    retrieval_timestamp="2026-10-19 10:00:00",
                ),
                "Retail": SubscriptionCategory(
                    shares_offered=100000,
                    shares_bid=650000,
                    subscription_multiple=6.5,
                    source="NSE Live",
                    source_date="2026-10-19",
                    retrieval_timestamp="2026-10-19 10:00:00",
                ),
                "Total": SubscriptionCategory(
                    shares_offered=300000,
                    shares_bid=5350000,
                    subscription_multiple=17.83,
                    source="NSE Live",
                    source_date="2026-10-19",
                    retrieval_timestamp="2026-10-19 10:00:00",
                ),
            }

        list_item = _to_list_item(rec)
        self.assertEqual(list_item.qib_subscription, 32.0)
        self.assertEqual(list_item.nii_subscription, 15.0)
        self.assertEqual(list_item.retail_subscription, 6.5)
        self.assertAlmostEqual(list_item.subscription_times, 17.83)
        self.assertIn("QIB: 32.0x", list_item.subscription_summary)


class TestPhase4FinancialsBridge(unittest.TestCase):
    """Tests for Phase 4: Financials Bridge Adapter and Ratios Calculation."""

    def setUp(self):
        self.adapter = FinancialsBridgeAdapter()

    def test_normalize_period_label(self):
        self.assertEqual(self.adapter._normalize_period_label("31 Mar 2024"), "FY2024")
        self.assertEqual(self.adapter._normalize_period_label("31 Mar 2023"), "FY2023")
        self.assertEqual(self.adapter._normalize_period_label("FY24"), "FY2024")
        self.assertEqual(self.adapter._normalize_period_label("FY2025"), "FY2025")

    def test_build_financial_records_computes_growth_and_ratios(self):
        raw_periods = [
            {
                "period": "FY2022",
                "revenue": 100.0,
                "pat": 10.0,
                "net_worth": 50.0,
                "debt": 25.0,
                "ebitda": 20.0,
            },
            {
                "period": "FY2023",
                "revenue": 130.0,
                "pat": 15.0,
                "net_worth": 65.0,
                "debt": 20.0,
                "ebitda": 28.0,
            },
            {
                "period": "FY2024",
                "revenue": 182.0,
                "pat": 24.0,
                "net_worth": 89.0,
                "debt": 15.0,
                "ebitda": 40.0,
            },
        ]

        records = self.adapter.build_financial_records(raw_periods)
        self.assertEqual(len(records), 3)

        # FY22 (Baseline)
        fy22 = records[0]
        self.assertEqual(fy22.financial_period, "FY2022")
        self.assertEqual(fy22.revenue.value, 100.0)
        self.assertEqual(fy22.ROE.value, 20.0)  # 10 / 50 * 100
        self.assertEqual(fy22.debt_equity.value, 0.50)  # 25 / 50
        self.assertIsNone(fy22.revenue_growth)

        # FY23 (Year 1 growth)
        fy23 = records[1]
        self.assertEqual(fy23.revenue.value, 130.0)
        self.assertEqual(fy23.revenue_growth.value, 30.0)  # (130-100)/100 * 100
        self.assertEqual(fy23.PAT_growth.value, 50.0)  # (15-10)/10 * 100
        self.assertAlmostEqual(fy23.ROE.value, 23.08, places=2)  # 15 / 65 * 100
        self.assertAlmostEqual(fy23.debt_equity.value, 0.31, places=2)

        # FY24 (Year 2 growth)
        fy24 = records[2]
        self.assertEqual(fy24.revenue.value, 182.0)
        self.assertEqual(fy24.revenue_growth.value, 40.0)  # (182-130)/130 * 100
        self.assertEqual(fy24.PAT_growth.value, 60.0)  # (24-15)/15 * 100
        self.assertAlmostEqual(fy24.ROE.value, 26.97, places=2)
        self.assertAlmostEqual(fy24.debt_equity.value, 0.17, places=2)

    def test_sync_financials_api_route(self):
        client = TestClient(create_app())
        token = create_access_token(principal_id="operator_user", role=Role.OPERATOR)
        headers = {"Authorization": f"Bearer {token}"}

        # Mock adapter
        with patch.object(
            FinancialsBridgeAdapter,
            "sync_financials_for_ipo",
            return_value={
                "ipo_id": "IPO-TEST-2026",
                "company_name": "Test Robotics Ltd",
                "status": "synced",
                "periods_synced": 3,
                "latest_period": "FY2024",
                "latest_revenue_cr": 182.0,
                "latest_pat_cr": 24.0,
                "latest_roe_pct": 26.97,
                "latest_de_ratio": 0.17,
                "latest_pat_growth_pct": 60.0,
            },
        ):
            # Test 404 for unknown IPO
            res = client.post("/ipos/NON-EXISTENT-999/sync-financials", headers=headers)
            self.assertEqual(res.status_code, 404)
