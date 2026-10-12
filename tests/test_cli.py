"""
Unit Tests for Operational CLI.
Verifies CLI command execution, argument parsing, error handling, exit codes,
and integration with underlying application services.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.cli import main
from ipo_platform.db import get_engine, init_db


class TestCLI(unittest.TestCase):
    def setUp(self):
        """Sets up isolated temporary directory and test database."""
        self.test_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.test_dir, "test_cli.db")
        self.db_url = f"sqlite:///{self.db_file}"

        # Initialize schema in test database
        engine = get_engine(self.db_url)
        init_db(engine)

        self.reports_dir = os.path.join(self.test_dir, "reports")

        # Create sample JSON file for ingestion testing
        self.sample_record = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "TEST-CLI-001",
                "company_name": "CLI Enterprise Solutions Ltd",
                "company_legal_name": "CLI Enterprise Solutions Limited",
                "ticker_symbol": "CLIENTER",
                "isin": "INE009A01011",
                "segment": "Mainboard",
                "sector": "Information Technology",
                "industry": "Software",
            },
            "ipo_status": {
                "status": "Currently Open",
                "research_date": "2026-10-01",
                "research_time": "09:30:00",
                "data_cutoff": "2026-10-01 09:30:00",
                "open_date": "2026-10-01",
                "close_date": "2026-10-03",
                "listing_date": "2026-10-07",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 500.0, "unit": "Crores"},
                "fresh_issue_amount": {"value": 300.0, "unit": "Crores"},
                "ofs_amount": {"value": 200.0, "unit": "Crores"},
                "fresh_issue_percentage": {"value": 60.0},
                "ofs_percentage": {"value": 40.0},
                "face_value": {"value": 10.0},
                "price_band_low": {"value": 190.0},
                "price_band_high": {"value": 200.0},
                "issue_price": {"value": 200.0},
                "lot_size": {"value": 75},
                "minimum_investment": {"value": 15000.0},
            },
            "valuation_data": {
                "reference_price": 200.0,
                "reference_eps": 8.0,
                "issue_pe": {"value": 25.0},
                "valuation_method": "Relative PE",
                "valuation_source": "RHP",
                "valuation_date": "2026-10-01",
            },
            "scenario_40_percent": {
                "reference_price": 200.0,
                "target_price": 280.0,
                "required_price_movement": 40.0,
                "target_pe": 35.0,
                "supporting_factors": ["Strong tech pipeline"],
                "contradictory_factors": [],
                "scenario_status": "Supported",
                "scenario_methodology": "Standardized non-predictive model",
                "scenario_data_timestamp": "2026-10-01 09:30:00",
            },
            "data_quality": {
                "completeness_status": "Complete",
                "source_verification_status": "Verified",
                "last_verified": "2026-10-01 09:30:00",
            },
        }
        self.sample_json_path = os.path.join(self.test_dir, "sample_ipo.json")
        with open(self.sample_json_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_record, f)

    def tearDown(self):
        """Removes temporary test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_cli_ingest_success(self):
        code = main(["--db-url", self.db_url, "ingest", "--file", self.sample_json_path])
        self.assertEqual(code, 0)

    def test_cli_ingest_missing_file_arg(self):
        with patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--db-url", self.db_url, "ingest"])
            self.assertIn(cm.exception.code, (1, 2))

    def test_cli_ingest_nonexistent_file(self):
        with patch("sys.stderr", new=io.StringIO()) as err_buf:
            code = main(["--db-url", self.db_url, "ingest", "--file", "nonexistent_file.json"])
            self.assertEqual(code, 2)
            self.assertIn("does not exist", err_buf.getvalue())

    def test_cli_ingest_invalid_json(self):
        bad_json_path = os.path.join(self.test_dir, "bad.json")
        with open(bad_json_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true")

        with patch("sys.stderr", new=io.StringIO()) as err_buf:
            code = main(["--db-url", self.db_url, "ingest", "--file", bad_json_path])
            self.assertEqual(code, 2)
            self.assertIn("Invalid JSON syntax", err_buf.getvalue())

    def test_cli_list_command(self):
        # First ingest
        main(["--db-url", self.db_url, "ingest", "--file", self.sample_json_path])

        # Test list all
        with patch("sys.stdout", new=io.StringIO()) as out_buf:
            code = main(["--db-url", self.db_url, "list"])
            self.assertEqual(code, 0)
            self.assertIn("CLI Enterprise Solutions Ltd", out_buf.getvalue())

        # Test list with status filter
        with patch("sys.stdout", new=io.StringIO()) as out_buf:
            code = main(["--db-url", self.db_url, "list", "--status", "Currently Open"])
            self.assertEqual(code, 0)
            self.assertIn("CLI Enterprise Solutions Ltd", out_buf.getvalue())

    def test_cli_list_invalid_status(self):
        with patch("sys.stderr", new=io.StringIO()) as err_buf:
            code = main(["--db-url", self.db_url, "list", "--status", "InvalidStatusName"])
            self.assertEqual(code, 2)
            self.assertIn("Invalid IPO status", err_buf.getvalue())

    def test_cli_briefing_command(self):
        # First ingest
        main(["--db-url", self.db_url, "ingest", "--file", self.sample_json_path])

        with patch("sys.stdout", new=io.StringIO()) as out_buf:
            code = main([
                "--db-url", self.db_url,
                "briefing",
                "--date", "2026-10-01",
                "--output-dir", self.reports_dir,
                "--print",
            ])
            self.assertEqual(code, 0)
            self.assertIn("Daily Briefing Report generated successfully", out_buf.getvalue())
            self.assertIn("CLI Enterprise Solutions Ltd", out_buf.getvalue())

        generated_file = os.path.join(self.reports_dir, "briefing_2026-10-01.md")
        self.assertTrue(os.path.isfile(generated_file))

    def test_cli_briefing_invalid_date(self):
        with patch("sys.stderr", new=io.StringIO()) as err_buf:
            code = main(["--db-url", self.db_url, "briefing", "--date", "invalid-date-format"])
            self.assertEqual(code, 2)
            self.assertIn("Invalid date format", err_buf.getvalue())

    def test_cli_migrate_command(self):
        with patch("sys.stdout", new=io.StringIO()) as out_buf:
            code = main(["--db-url", self.db_url, "migrate"])
            self.assertEqual(code, 0)
            self.assertTrue(
                "Alembic" in out_buf.getvalue() or "synchronized" in out_buf.getvalue()
            )

    def test_cli_backtest_command(self):
        # Ingest record first
        main(["--db-url", self.db_url, "ingest", "--file", self.sample_json_path])

        with patch("sys.stdout", new=io.StringIO()) as out_buf:
            code = main(["--db-url", self.db_url, "backtest", "--json"])
            self.assertEqual(code, 0)
            self.assertIn("Backtest Simulation Summary", out_buf.getvalue())

    def test_cli_no_command_returns_code_2(self):
        with patch("sys.stderr", new=io.StringIO()):
            code = main([])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
