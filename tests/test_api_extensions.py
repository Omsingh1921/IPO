"""
Integration tests for new API routes and operational CLI commands (RHP parsing, live quote streams, and CDC workers).
"""

import os
import tempfile
import unittest
from fastapi.testclient import TestClient

from ipo_platform.api.app import create_app
from ipo_platform.api.dependencies import set_db_engine
from ipo_platform.cli import main as cli_main
from ipo_platform.db.session import get_engine, init_db
from ipo_platform.security import Role, create_access_token


class TestAPIExtensionsAndCLI(unittest.TestCase):
    """Test suite validating API extensions and new CLI subcommands."""

    @classmethod
    def setUpClass(cls):
        cls.engine = get_engine("sqlite:///:memory:")
        init_db(cls.engine)
        set_db_engine(cls.engine)

        cls.app = create_app()
        cls.client = TestClient(cls.app)

        cls.readonly_token = create_access_token(principal_id="test-readonly", role=Role.READ_ONLY)
        cls.operator_token = create_access_token(principal_id="test-operator", role=Role.OPERATOR)

    def test_stream_live_quotes_endpoint(self):
        headers = {"Authorization": f"Bearer {self.readonly_token}"}
        resp = self.client.get("/ipos/stream/live-quotes", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("quotes", data)
        self.assertIn("server_time", data)

    def test_parse_rhp_api_endpoint(self):
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        sample_text = """
        Company Name: Apex Advanced Materials Ltd
        Issue Price: ₹380
        Total Issue Size: ₹450 Crore
        Revenue from Operations: ₹620 Crore
        Profit After Tax: ₹78 Crore
        """
        payload = {
            "text": sample_text,
            "source_id": "SRC-TEST-API",
            "ingest": False,
        }
        resp = self.client.post("/ipos/parse-rhp", json=payload, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("Apex Advanced", data["company_name"])
        self.assertEqual(data["financials"]["revenue_cr"], 620.0)

    def test_cli_parse_rhp_command(self):
        sample_filing = "Company Name: SolarGrid Technologies Ltd\nOffer Price: ₹210\nTotal Issue Size: ₹350 Crore"
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
            f.write(sample_filing)
            tmp_path = f.name

        try:
            exit_code = cli_main(["parse-rhp", "--file", tmp_path])
            self.assertEqual(exit_code, 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_consume_cdc_max_iterations(self):
        exit_code = cli_main(["consume-cdc", "--max-iterations", "1"])
        self.assertEqual(exit_code, 0)

    def test_auth_login_success(self):
        resp = self.client.post("/auth/login", json={"key_or_password": "key-admin-789"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "ADMIN")
        self.assertEqual(data["token_type"], "bearer")

        # Verify /auth/me with the received token
        me_resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertTrue(me_data["authenticated"])
        self.assertEqual(me_data["role"], "ADMIN")

    def test_auth_login_failure(self):
        resp = self.client.post("/auth/login", json={"key_or_password": "wrong-secret-key"})
        self.assertEqual(resp.status_code, 401)

    def test_ipos_sync_endpoint(self):
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        resp = self.client.post("/ipos/sync?dry_run=true", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["dry_run"])
        self.assertIn("synced_at", data)
        self.assertIn("total_sources", data)

    def test_wishlist_crud_and_history_endpoints(self):
        from ipo_platform.db.models import IPOMasterModel
        from sqlalchemy.orm import Session
        import datetime

        # Seed a test IPO into database
        with Session(self.engine) as db:
            test_ipo = IPOMasterModel(
                ipo_id="TEST-CORP-2026",
                company_name="Test Corp India Ltd",
                company_legal_name="Test Corporation India Private Limited",
                status="Closed",
                listing_status="Listed",
                segment="Mainboard",
                sector="Technology",
                industry="Software",
                research_date=datetime.date(2026, 10, 1),
                research_time=datetime.time(10, 0),
                data_cutoff=datetime.datetime(2026, 10, 1, 10, 0),
                open_date=datetime.date(2026, 10, 5),
                close_date=datetime.date(2026, 10, 8),
                listing_date=datetime.date(2026, 10, 10),
                issue_size=500.0,
                face_value=10.0,
                price_band_high=200.0,
                issue_price=200.0,
                lot_size=50,
                minimum_investment=10000.0,
            )
            db.merge(test_ipo)
            db.commit()

        headers = {"Authorization": f"Bearer {self.readonly_token}"}

        # 1. Add to wishlist
        add_resp = self.client.post("/wishlist/TEST-CORP-2026", headers=headers)
        self.assertIn(add_resp.status_code, (200, 201))
        self.assertIn(add_resp.json()["status"], ("added", "exists"))

        # 2. Verify in wishlist ids
        ids_resp = self.client.get("/wishlist/ids", headers=headers)
        self.assertEqual(ids_resp.status_code, 200)
        self.assertIn("TEST-CORP-2026", ids_resp.json()["wishlist"])

        # 3. Verify in full wishlist
        list_resp = self.client.get("/wishlist", headers=headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertGreaterEqual(list_resp.json()["total"], 1)

        # 4. Check post-listing history auto-sync
        hist_resp = self.client.get("/wishlist/history", headers=headers)
        self.assertEqual(hist_resp.status_code, 200)
        hist_data = hist_resp.json()
        self.assertGreaterEqual(hist_data["total"], 1)
        found = any(item["ipo_id"] == "TEST-CORP-2026" for item in hist_data["items"])
        self.assertTrue(found)

        # 5. Record/Update actual listing price
        record_resp = self.client.post(
            "/wishlist/history/TEST-CORP-2026",
            json={
                "listing_price": 250.0,
                "listing_day_close": 255.0,
                "notes": "Listed at 25% premium"
            },
            headers=headers
        )
        self.assertEqual(record_resp.status_code, 200)
        saved = record_resp.json()
        self.assertEqual(saved["listing_price"], 250.0)
        self.assertEqual(saved["issue_price"], 200.0)
        self.assertEqual(saved["listing_gain_pct"], 25.0)
        self.assertEqual(saved["listing_day_close"], 255.0)

        # 6. Verify sync endpoint
        sync_resp = self.client.post("/wishlist/history/sync", headers=headers)
        self.assertEqual(sync_resp.status_code, 200)

        # 7. Remove from history
        del_hist = self.client.delete("/wishlist/history/TEST-CORP-2026", headers=headers)
        self.assertEqual(del_hist.status_code, 200)
        self.assertEqual(del_hist.json()["status"], "removed")

        # 8. Remove from active wishlist
        del_wish = self.client.delete("/wishlist/TEST-CORP-2026", headers=headers)
        self.assertEqual(del_wish.status_code, 200)
        self.assertEqual(del_wish.json()["status"], "removed")


if __name__ == "__main__":
    unittest.main()



