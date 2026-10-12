import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ipo_platform.engine.scenario_evaluator import Scenario40PercentEvaluator
from src.ipo_platform.engine.validators import IPOValidator
from src.ipo_platform.models.enums import ScenarioStatusEnum



class TestScenarioEvaluator(unittest.TestCase):
    def test_target_price_math(self):
        scenario = Scenario40PercentEvaluator.create_scenario(
            reference_price=34.00,
            reference_eps=0.79,
            supporting_factors=["Strong Q1 profit", "Anchor participation"],
            contradictory_factors=["Sluggish FY26 annual growth"],
            timestamp="2026-09-24 11:00:00",
        )
        self.assertEqual(scenario.reference_price, 34.00)
        self.assertEqual(scenario.target_price, 47.60)
        self.assertEqual(scenario.required_price_movement, 40.00)
        self.assertEqual(scenario.target_pe, 60.25)
        self.assertEqual(scenario.scenario_status, ScenarioStatusEnum.SUPPORTED)

        valid, errors = IPOValidator.validate_scenario_math(scenario)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_prohibited_keys_detector(self):
        sample_bad_data = {
            "ipo_id": "TEST-01",
            "recommendation": "BUY",  # Prohibited!
            "inner": {"guaranteed_return": 40},  # Prohibited!
        }
        violations = IPOValidator.validate_prohibited_keys(sample_bad_data)
        self.assertEqual(len(violations), 2)
        self.assertIn("recommendation", violations[0])


if __name__ == "__main__":
    unittest.main()
