import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ipo_platform.engine.ratio_calculator import RatioCalculator



class TestRatioCalculator(unittest.TestCase):
    def test_yoy_growth(self):
        growth = RatioCalculator.calculate_yoy_growth(2378.53, 3404.27)
        self.assertAlmostEqual(growth, 43.12, places=2)

        growth_pat = RatioCalculator.calculate_yoy_growth(240.28, 242.71)
        self.assertAlmostEqual(growth_pat, 1.01, places=2)

    def test_ebitda_margin(self):
        margin = RatioCalculator.calculate_ebitda_margin(968.92, 3404.27)
        self.assertAlmostEqual(margin, 28.46, places=2)

    def test_pe_ratio(self):
        pe = RatioCalculator.calculate_pe(34.00, 0.79)
        self.assertAlmostEqual(pe, 43.04, places=2)

    def test_valuation_spread(self):
        spread = RatioCalculator.calculate_valuation_spread(43.04, 28.50)
        self.assertAlmostEqual(spread, 51.02, places=2)

    def test_null_handling(self):
        self.assertIsNone(RatioCalculator.calculate_pe(34.00, None))
        self.assertIsNone(RatioCalculator.calculate_yoy_growth(None, 100.0))


if __name__ == "__main__":
    unittest.main()
