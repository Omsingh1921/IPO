import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ipo_platform.sheets.sheets_schema import GOOGLE_SHEETS_TAB_HEADERS, SheetTabName
from src.ipo_platform.sheets.sheets_validator import SheetsTabularValidator
from src.ipo_platform.sheets.sheets_mapper import SheetsDataMapper
from src.ipo_platform.io.json_ingestor import JSONIngestor


class TestSheetsImplementation(unittest.TestCase):
    def setUp(self):
        self.sample_json = {
            "schema_version": "1.0",
            "ipo_entity": {
                "ipo_id": "IND-MB-2026-MONEYVIEW",
                "company_name": "Moneyview Limited",
                "company_legal_name": "Whizdm Innovations Private Limited",
                "ticker_symbol": "MONEYVIEW",
                "isin": "Not available",
                "segment": "Mainboard",
                "sector": "Fintech / Financial Services",
                "industry": "Digital Lending Platforms",
            },
            "ipo_status": {
                "status": "Opening Today",
                "research_date": "2026-09-24",
                "research_time": "11:15:00",
                "data_cutoff": "2026-09-24 10:45:00",
                "open_date": "2026-09-24",
                "close_date": "2026-09-28",
                "listing_date": "2026-10-01",
                "listing_status": "Pre-Listing",
            },
            "issue_structure": {
                "issue_size": {"value": 1091.68, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_amount": {"value": 750.00, "unit": "Crores", "data_type": "Reported"},
                "ofs_amount": {"value": 341.68, "unit": "Crores", "data_type": "Reported"},
                "fresh_issue_percentage": {"value": 68.70, "data_type": "Calculated"},
                "ofs_percentage": {"value": 31.30, "data_type": "Calculated"},
                "face_value": {"value": 1.00, "data_type": "Reported"},
                "price_band_low": {"value": 32.00, "data_type": "Reported"},
                "price_band_high": {"value": 34.00, "data_type": "Reported"},
                "issue_price": {"value": "Not available", "data_type": "Not available"},
                "lot_size": {"value": 441, "data_type": "Reported"},
                "minimum_investment": {"value": 14994.00, "data_type": "Calculated"},
            },
            "valuation_data": {
                "reference_price": 34.00,
                "reference_eps": 0.79,
                "issue_pe": {"value": 43.04, "data_type": "Calculated"},
                "valuation_method": "Trailing Diluted P/E on FY26 Earnings",
                "valuation_source": "RHP Financial Statements",
                "valuation_date": "2026-09-24",
            },
            "scenario_40_percent": {
                "reference_price": 34.00,
                "target_price": 47.60,
                "required_price_movement": 40.00,
                "target_pe": 60.25,
                "supporting_factors": ["GMP quote"],
                "contradictory_factors": ["FY26 PAT growth"],
                "scenario_status": "Insufficient evidence",
                "scenario_methodology": "Standardized non-predictive model",
                "scenario_data_timestamp": "2026-09-24 11:00:00",
            },
            "data_quality": {
                "completeness_status": "Partial",
                "source_verification_status": "Verified",
                "last_verified": "2026-09-24 10:45:00",
            },
        }

    def test_header_validation(self):
        valid_headers = GOOGLE_SHEETS_TAB_HEADERS[SheetTabName.IPO_MASTER]
        valid, errors = SheetsTabularValidator.validate_headers(SheetTabName.IPO_MASTER, valid_headers)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_prohibited_header_rejection(self):
        bad_headers = GOOGLE_SHEETS_TAB_HEADERS[SheetTabName.IPO_MASTER] + ["recommendation"]
        valid, errors = SheetsTabularValidator.validate_headers(SheetTabName.IPO_MASTER, bad_headers)
        self.assertFalse(valid)
        self.assertIn("recommendation", errors[0])

    def test_scenario_tab_math_validation(self):
        valid_row = {"reference_price": 34.00, "target_price_40": 47.60, "required_move": 40.00}
        valid, errors = SheetsTabularValidator.validate_scenario_row(valid_row)
        self.assertTrue(valid)

        bad_row = {"reference_price": 34.00, "target_price_40": 55.00, "required_move": 40.00}
        valid, errors = SheetsTabularValidator.validate_scenario_row(bad_row)
        self.assertFalse(valid)

    def test_data_mapper(self):
        record = JSONIngestor.from_dict(self.sample_json)
        tabular_dict = SheetsDataMapper.record_to_tabular(record)

        self.assertIn(SheetTabName.IPO_MASTER, tabular_dict)
        self.assertIn(SheetTabName.SCENARIOS, tabular_dict)

        master_row = tabular_dict[SheetTabName.IPO_MASTER][0]
        self.assertEqual(master_row["ipo_id"], "IND-MB-2026-MONEYVIEW")
        self.assertEqual(master_row["segment"], "Mainboard")

        scenario_row = tabular_dict[SheetTabName.SCENARIOS][0]
        self.assertEqual(scenario_row["target_price_40"], 47.60)
        self.assertEqual(scenario_row["required_move"], 40.00)


if __name__ == "__main__":
    unittest.main()
