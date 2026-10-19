"""
Unit and regression tests for RHP / DRHP automated prospectus parser.
"""

import unittest
from ipo_platform.analysis.rhp_parser import RHPProspectusParser
from ipo_platform.models.schema import MasterIPORecord


SAMPLE_RHP_TEXT = """
Draft Red Herring Prospectus Dated October 15, 2026
Please read Section 32 of the Companies Act, 2013

Company Name: Bharat Solar Power Infrastructure Limited
CIN: L40106MH2019PLC312456
Registered Office: Nariman Point, Mumbai 400021, Maharashtra, India

Issue Structure:
The Offer comprises a Fresh Issue of Equity Shares aggregating up to ₹600.00 Crore 
and an Offer for Sale (OFS) aggregating up to ₹400.00 Crore.
Total Issue Size: Aggregating up to ₹1000.00 Crore.
Price Band: ₹450 to ₹475 per Equity Share of face value of ₹10 each.
Minimum Bid Quantity: 30 Equity Shares and in multiples of 30 Equity Shares thereafter.
Issue Opens on: 2026-11-04
Issue Closes on: 2026-11-07

Summary of Restated Financial Information:
Revenue from Operations: ₹1250.00 Crore
Profit After Tax: ₹165.50 Crore
EBITDA: ₹310.00 Crore
Total Borrowings: ₹220.00 Crore
Net Worth: ₹750.00 Crore
Implied P/E: 28.50

Objects of the Issue:
- Object 1: Capital expenditure for setting up 250 MW solar installation: ₹350.00 Crore
- Object 2: Prepayment or repayment of certain borrowings: ₹150.00 Crore
- Object 3: General corporate purposes: ₹100.00 Crore

Key Risk Factors:
- The business is subject to substantial dependence on key photovoltaic cell suppliers in Asia.
- Material regulatory litigations and tax proceedings pending before judicial authorities.
- Counterparty credit risk with state distribution utilities resulting in delayed payments.
"""


class TestRHPProspectusParser(unittest.TestCase):
    """Test suite validating SEBI prospectus text extraction and record building."""

    def test_parse_sample_prospectus(self):
        record = RHPProspectusParser.parse_prospectus_text(SAMPLE_RHP_TEXT)
        self.assertIsInstance(record, MasterIPORecord)

        # Entity checks
        self.assertIn("Bharat Solar", record.ipo_entity.company_name)
        self.assertEqual(record.ipo_entity.isin, "INEBHARAT0101")

        # Structure checks (wrapped in ProvenanceEnvelope)
        self.assertEqual(record.issue_structure.price_band_low.value, 450.0)
        self.assertEqual(record.issue_structure.price_band_high.value, 475.0)
        self.assertEqual(record.issue_structure.lot_size.value, 30)
        self.assertEqual(record.issue_structure.issue_size.value, 1000.0)
        self.assertEqual(record.issue_structure.fresh_issue_amount.value, 600.0)
        self.assertEqual(record.issue_structure.ofs_amount.value, 400.0)

        # Financials checks
        self.assertEqual(len(record.financial_data), 1)
        fin = record.financial_data[0]
        self.assertEqual(fin.revenue.value, 1250.0)
        self.assertEqual(fin.PAT.value, 165.5)
        self.assertEqual(fin.EBITDA.value, 310.0)
        self.assertEqual(fin.total_debt.value, 220.0)
        self.assertGreater(fin.ROE.value, 0.0)

        # Objects & Risks
        self.assertGreaterEqual(len(record.objects_of_issue), 1)
        self.assertGreaterEqual(len(record.risk_data), 1)

        # 40% Target Hypothesis Check
        self.assertEqual(record.scenario_40_percent.target_price, round(475.0 * 1.40, 2))

    def test_parse_sparse_prospectus_with_fallbacks(self):
        sparse_text = "Name of the Company: Acme Industrial Solutions Ltd\nOffer Price: ₹250"
        record = RHPProspectusParser.parse_prospectus_text(sparse_text)
        self.assertEqual(record.ipo_entity.company_name, "Acme Industrial Solutions Ltd")
        self.assertEqual(record.issue_structure.price_band_high.value, 250.0)
        self.assertGreater(record.financial_data[0].revenue.value, 0.0)
        self.assertGreater(len(record.risk_data), 0)


if __name__ == "__main__":
    unittest.main()
