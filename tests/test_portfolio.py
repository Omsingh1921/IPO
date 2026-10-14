"""
Comprehensive Unit Tests for Portfolio Strategy & Capital Allocation Engine (Phase 10 - Stage 3).
Validates:
- Allocation rules by RecommendationCategory and RiskProfile.
- Capital allocation percentages, position sizes, and cash balances.
- Diversification limits (single IPO <= 35%, sector <= 40%, total <= 100%).
- PortfolioRiskEngine analytics (Sharpe, Expected Return, Expected Risk, HHI).
- Serialization: to_dict() and to_json().
- Edge cases: zero capital, empty cohort, all AVOID recommendations, over-allocation scaling.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ipo_platform.portfolio.allocation_models import (
    AllocationStrategy,
    CapitalAllocation,
    PortfolioRecommendation,
    PortfolioRiskCategory,
    RiskProfile,
)
from ipo_platform.portfolio.portfolio_engine import IPOPortfolioEngine
from ipo_platform.portfolio.risk_engine import PortfolioRiskEngine
from ipo_platform.recommendation.recommendation_result import RecommendationResult
from ipo_platform.recommendation.scoring_models import (
    FactorScore,
    RecommendationCategory,
    RiskLevel,
)


class TestPortfolioAllocationEngine(unittest.TestCase):
    """Unit tests for the portfolio allocation and risk engine."""

    def setUp(self):
        self.engine = IPOPortfolioEngine()

    def _create_rec(
        self,
        ipo_id: str,
        company_name: str,
        category: RecommendationCategory,
        composite_score: float = 75.0,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> RecommendationResult:
        return RecommendationResult(
            ipo_id=ipo_id,
            company_name=company_name,
            recommendation=category,
            composite_score=composite_score,
            confidence_score=0.95,
            risk_level=risk_level,
            factor_scores={},
            strengths=["Strong market backing"],
            risks=[],
            veto_applied=None,
            summary_rationale="Solid investment opportunity",
        )

    # 1. Allocation Rules by Category and Risk Profile
    def test_allocation_rules_aggressive_profile(self):
        rec_strong = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE, 90.0)
        rec_sub = self._create_rec("IPO-2", "Beta Finance", RecommendationCategory.SUBSCRIBE, 70.0)
        rec_neu = self._create_rec("IPO-3", "Gamma Power", RecommendationCategory.NEUTRAL, 50.0)
        rec_avoid = self._create_rec("IPO-4", "Delta Infra", RecommendationCategory.AVOID, 25.0)

        res = self.engine.allocate_portfolio(
            recommendations=[rec_strong, rec_sub, rec_neu, rec_avoid],
            available_capital=1000000.0,  # 10 Lakhs INR
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        alloc_map = {a.ipo_id: a for a in res.allocations}
        # Strong Subscribe = 35%
        self.assertEqual(alloc_map["IPO-1"].allocation_percentage, 35.0)
        self.assertEqual(alloc_map["IPO-1"].allocated_amount, 350000.0)
        # Subscribe = 20%
        self.assertEqual(alloc_map["IPO-2"].allocation_percentage, 20.0)
        self.assertEqual(alloc_map["IPO-2"].allocated_amount, 200000.0)
        # Neutral = 10%
        self.assertEqual(alloc_map["IPO-3"].allocation_percentage, 10.0)
        self.assertEqual(alloc_map["IPO-3"].allocated_amount, 100000.0)
        # Avoid = 0%
        self.assertEqual(alloc_map["IPO-4"].allocation_percentage, 0.0)
        self.assertEqual(alloc_map["IPO-4"].allocated_amount, 0.0)

        # Total allocated = 65% (6.5 Lakhs), unallocated cash = 35% (3.5 Lakhs)
        self.assertEqual(res.total_allocation_percentage, 65.0)
        self.assertEqual(res.total_allocated_capital, 650000.0)
        self.assertEqual(res.unallocated_cash, 350000.0)

    def test_allocation_rules_moderate_profile(self):
        rec_strong = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE, 85.0)
        rec_sub = self._create_rec("IPO-2", "Beta Finance", RecommendationCategory.SUBSCRIBE, 68.0)
        rec_neu = self._create_rec("IPO-3", "Gamma Power", RecommendationCategory.NEUTRAL, 52.0)
        rec_avoid = self._create_rec("IPO-4", "Delta Infra", RecommendationCategory.AVOID, 30.0)

        res = self.engine.allocate_portfolio(
            recommendations=[rec_strong, rec_sub, rec_neu, rec_avoid],
            available_capital=1000000.0,
            risk_profile=RiskProfile.MODERATE,
        )

        alloc_map = {a.ipo_id: a for a in res.allocations}
        # Moderate: Strong Subscribe 25%, Subscribe 15%, Neutral 5%, Avoid 0%
        self.assertEqual(alloc_map["IPO-1"].allocation_percentage, 25.0)
        self.assertEqual(alloc_map["IPO-2"].allocation_percentage, 15.0)
        self.assertEqual(alloc_map["IPO-3"].allocation_percentage, 5.0)
        self.assertEqual(alloc_map["IPO-4"].allocation_percentage, 0.0)

        self.assertEqual(res.total_allocation_percentage, 45.0)
        self.assertEqual(res.total_allocated_capital, 450000.0)
        self.assertEqual(res.unallocated_cash, 550000.0)

    def test_allocation_rules_conservative_profile(self):
        rec_strong = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE, 88.0)
        rec_sub = self._create_rec("IPO-2", "Beta Finance", RecommendationCategory.SUBSCRIBE, 70.0)
        rec_neu = self._create_rec("IPO-3", "Gamma Power", RecommendationCategory.NEUTRAL, 50.0)
        rec_avoid = self._create_rec("IPO-4", "Delta Infra", RecommendationCategory.AVOID, 20.0)

        res = self.engine.allocate_portfolio(
            recommendations=[rec_strong, rec_sub, rec_neu, rec_avoid],
            available_capital=1000000.0,
            risk_profile=RiskProfile.CONSERVATIVE,
        )

        alloc_map = {a.ipo_id: a for a in res.allocations}
        # Conservative: Strong Subscribe 15%, Subscribe 10%, Neutral 0%, Avoid 0%
        self.assertEqual(alloc_map["IPO-1"].allocation_percentage, 15.0)
        self.assertEqual(alloc_map["IPO-2"].allocation_percentage, 10.0)
        self.assertEqual(alloc_map["IPO-3"].allocation_percentage, 0.0)
        self.assertEqual(alloc_map["IPO-4"].allocation_percentage, 0.0)

        self.assertEqual(res.total_allocation_percentage, 25.0)
        self.assertEqual(res.total_allocated_capital, 250000.0)
        self.assertEqual(res.unallocated_cash, 750000.0)

    # 2. Diversification Constraints: Single IPO Cap <= 35%
    def test_single_ipo_cap_constraint(self):
        strategy = AllocationStrategy(profile=RiskProfile.AGGRESSIVE, max_single_ipo_pct=35.0)
        self.assertLessEqual(strategy.get_base_allocation_pct(RecommendationCategory.STRONG_SUBSCRIBE), 35.0)

        rec = self._create_rec("IPO-MAX", "Super IPO", RecommendationCategory.STRONG_SUBSCRIBE, 99.0)
        res = self.engine.allocate_single(rec, available_capital=500000.0, risk_profile=RiskProfile.AGGRESSIVE)
        self.assertLessEqual(res.allocations[0].allocation_percentage, 35.0)
        self.assertEqual(res.allocations[0].allocated_amount, 175000.0)

    # 3. Diversification Constraints: Sector Concentration Limit <= 40%
    def test_sector_concentration_constraint(self):
        # 3 Strong Subscribes in same 'Technology' sector
        # Under Aggressive profile, 3 * 35% = 105% in Technology
        # Sector cap (40%) must cap subsequent Tech positions
        rec1 = self._create_rec("TECH-1", "Tech One", RecommendationCategory.STRONG_SUBSCRIBE, 95.0)
        rec2 = self._create_rec("TECH-2", "Tech Two", RecommendationCategory.STRONG_SUBSCRIBE, 90.0)
        rec3 = self._create_rec("TECH-3", "Tech Three", RecommendationCategory.STRONG_SUBSCRIBE, 85.0)

        tech_cohort = [
            (rec1, "Technology"),
            (rec2, "Technology"),
            (rec3, "Technology"),
        ]

        res = self.engine.allocate_portfolio(
            recommendations=tech_cohort,
            available_capital=1000000.0,
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        tech_allocations = [a for a in res.allocations if a.sector == "Technology"]
        total_tech_pct = sum(a.allocation_percentage for a in tech_allocations)

        self.assertLessEqual(total_tech_pct, 40.0)
        self.assertEqual(res.sector_allocations["Technology"], 40.0)
        self.assertTrue(any("concentration ceiling" in note for note in res.diversification_notes))

    # 4. Diversification Constraints: Total Capital Deployment <= 100%
    def test_total_capital_cap_pro_rata_scaling(self):
        # 5 Strong Subscribes across 5 different sectors: 5 * 35% = 175%
        recs = [
            (self._create_rec(f"IPO-{i}", f"Company {i}", RecommendationCategory.STRONG_SUBSCRIBE, 85.0), f"Sector-{i}")
            for i in range(5)
        ]

        res = self.engine.allocate_portfolio(
            recommendations=recs,
            available_capital=1000000.0,
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        self.assertLessEqual(res.total_allocation_percentage, 100.0)
        self.assertLessEqual(res.total_allocated_capital, 1000000.0)
        self.assertTrue(any("exceeded 100% capacity" in note for note in res.diversification_notes))

    # 5. Risk Engine & Portfolio Analytics
    def test_portfolio_risk_and_sharpe_calculations(self):
        rec_strong = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE, 90.0, RiskLevel.LOW)
        rec_sub = self._create_rec("IPO-2", "Beta Finance", RecommendationCategory.SUBSCRIBE, 70.0, RiskLevel.MEDIUM)

        res = self.engine.allocate_portfolio(
            recommendations=[rec_strong, rec_sub],
            available_capital=1000000.0,
            risk_profile=RiskProfile.MODERATE,
        )

        self.assertGreater(res.portfolio_risk_score, 0.0)
        self.assertIn(res.portfolio_risk_category, [PortfolioRiskCategory.LOW, PortfolioRiskCategory.MEDIUM, PortfolioRiskCategory.HIGH])
        self.assertGreater(res.expected_return, 0.0)
        self.assertGreater(res.expected_risk, 0.0)
        self.assertIsInstance(res.sharpe_score, float)
        self.assertGreater(res.concentration_risk, 0.0)
        self.assertGreater(res.exposure_risk, 0.0)

    # 6. Serialization to_dict() and to_json()
    def test_serialization_contracts(self):
        rec = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE, 90.0)
        res = self.engine.allocate_single(rec, available_capital=500000.0, risk_profile=RiskProfile.MODERATE)

        res_dict = res.to_dict()
        self.assertEqual(res_dict["total_capital"], 500000.0)
        self.assertEqual(res_dict["risk_profile"], "MODERATE")
        self.assertIn("allocations", res_dict)
        self.assertIn("portfolio_risk_score", res_dict)
        self.assertIn("sharpe_score", res_dict)

        res_json = res.to_json()
        self.assertIsInstance(res_json, str)
        parsed = json.loads(res_json)
        self.assertEqual(parsed["total_capital"], 500000.0)

        alloc = res.allocations[0]
        alloc_dict = alloc.to_dict()
        alloc_json = alloc.to_json()
        self.assertEqual(alloc_dict["ipo_id"], "IPO-1")
        self.assertIn("expected_return", json.loads(alloc_json))

    # 7. Edge Cases
    def test_zero_capital(self):
        rec = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE)
        res = self.engine.allocate_single(rec, available_capital=0.0)
        self.assertEqual(res.total_allocated_capital, 0.0)
        self.assertEqual(res.unallocated_cash, 0.0)
        self.assertEqual(len(res.allocations), 0)

    def test_negative_capital_raises_value_error(self):
        rec = self._create_rec("IPO-1", "Alpha Tech", RecommendationCategory.STRONG_SUBSCRIBE)
        with self.assertRaises(ValueError):
            self.engine.allocate_single(rec, available_capital=-5000.0)

    def test_all_avoid_cohort(self):
        rec1 = self._create_rec("IPO-A1", "Bad One", RecommendationCategory.AVOID, 20.0)
        rec2 = self._create_rec("IPO-A2", "Bad Two", RecommendationCategory.AVOID, 15.0)

        res = self.engine.allocate_portfolio(
            recommendations=[rec1, rec2],
            available_capital=500000.0,
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        self.assertEqual(res.total_allocated_capital, 0.0)
        self.assertEqual(res.total_allocation_percentage, 0.0)
        self.assertEqual(res.unallocated_cash, 500000.0)
        for a in res.allocations:
            self.assertEqual(a.allocated_amount, 0.0)

    # 8. Stage 3 Audit Regression Tests
    def test_duplicate_ipo_cannot_bypass_cap(self):
        """Duplicate IPO recommendations must not bypass single IPO limit (<= 35%)."""
        rec_a1 = self._create_rec("IPO-DUP", "Alpha Corp", RecommendationCategory.STRONG_SUBSCRIBE, 95.0)
        rec_a2 = self._create_rec("IPO-DUP", "Alpha Corp", RecommendationCategory.SUBSCRIBE, 75.0)

        # Pass duplicate entries for the same IPO
        res = self.engine.allocate_portfolio(
            recommendations=[rec_a1, rec_a2],
            available_capital=1000000.0,
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        dup_allocations = [a for a in res.allocations if a.ipo_id == "IPO-DUP"]
        # Must be consolidated into 1 position
        self.assertEqual(len(dup_allocations), 1)
        total_dup_pct = sum(a.allocation_percentage for a in dup_allocations)
        total_dup_amt = sum(a.allocated_amount for a in dup_allocations)

        self.assertLessEqual(total_dup_pct, 35.0)
        self.assertLessEqual(total_dup_amt, 350000.0)
        self.assertTrue(any("Duplicate recommendation" in note for note in res.diversification_notes))

    def test_rounding_cannot_exceed_100_percent_or_available_capital(self):
        """Mathematically valid allocation must never exceed 100% or available capital due to rounding."""
        # 3 positions under Moderate profile with 25% + 15% + 15% or pro-rata downscaled
        # Generate 7 positions to force fine fractions and fractional rounding
        recs = [
            (self._create_rec(f"IPO-R{i}", f"Company R{i}", RecommendationCategory.STRONG_SUBSCRIBE, 80.0 + i), f"Sector-{i}")
            for i in range(7)
        ]

        res = self.engine.allocate_portfolio(
            recommendations=recs,
            available_capital=333333.33,  # Fractional available capital
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        self.assertLessEqual(res.total_allocation_percentage, 100.0)
        self.assertLessEqual(res.total_allocated_capital, 333333.33)
        self.assertGreaterEqual(res.unallocated_cash, 0.0)
        # Verify exact invariant: total_allocated + unallocated == available
        self.assertAlmostEqual(
            res.total_allocated_capital + res.unallocated_cash,
            333333.33,
            places=2,
        )

    def test_missing_and_none_sector_normalization(self):
        """None or empty sector must normalize safely to General and respect sector limits."""
        rec1 = self._create_rec("IPO-S1", "No Sector 1", RecommendationCategory.STRONG_SUBSCRIBE, 90.0)
        rec2 = self._create_rec("IPO-S2", "No Sector 2", RecommendationCategory.STRONG_SUBSCRIBE, 85.0)

        res = self.engine.allocate_portfolio(
            recommendations=[(rec1, None), (rec2, "   ")],
            available_capital=1000000.0,
            risk_profile=RiskProfile.AGGRESSIVE,
        )

        for a in res.allocations:
            self.assertEqual(a.sector, "General")

        self.assertIn("General", res.sector_allocations)
        self.assertLessEqual(res.sector_allocations["General"], 40.0)

    def test_capital_preservation_invariant(self):
        """Capital deployed plus cash must strictly equal available capital across all profiles."""
        for prof in [RiskProfile.CONSERVATIVE, RiskProfile.MODERATE, RiskProfile.AGGRESSIVE]:
            recs = [
                self._create_rec(f"IPO-P{i}", f"Co P{i}", RecommendationCategory.STRONG_SUBSCRIBE if i % 2 == 0 else RecommendationCategory.SUBSCRIBE, 75.0 + i)
                for i in range(4)
            ]
            cap = 777777.77
            res = self.engine.allocate_portfolio(recommendations=recs, available_capital=cap, risk_profile=prof)
            self.assertLessEqual(res.total_allocated_capital, cap)
            self.assertLessEqual(res.total_allocation_percentage, 100.0)
            self.assertAlmostEqual(res.total_allocated_capital + res.unallocated_cash, cap, places=2)


if __name__ == "__main__":
    unittest.main()
