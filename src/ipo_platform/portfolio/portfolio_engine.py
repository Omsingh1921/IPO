"""
IPO Portfolio Engine Orchestrator (Phase 10 - Stage 3).
Executes capital allocation, risk optimization, diversification controls,
and portfolio-level analytics from RecommendationResult objects.
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union

from ipo_platform.portfolio.allocation_models import (
    AllocationStrategy,
    CapitalAllocation,
    PortfolioRecommendation,
    PortfolioRiskCategory,
    RiskProfile,
)
from ipo_platform.portfolio.risk_engine import PortfolioRiskEngine
from ipo_platform.recommendation.recommendation_result import RecommendationResult
from ipo_platform.recommendation.scoring_models import RecommendationCategory, RiskLevel

logger = logging.getLogger(__name__)


class IPOPortfolioEngine:
    """
    Quantitative Portfolio Strategy & Capital Allocation Engine.
    Allocates available investment capital across evaluated IPO offerings
    subject to strict risk profile constraints and diversification limits:
    - Maximum single IPO position: <= 35%
    - Total portfolio capital deployment: <= 100%
    - Maximum sector concentration: <= 40%
    """

    def __init__(
        self,
        strategy: Optional[AllocationStrategy] = None,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
    ) -> None:
        self.strategy = strategy or AllocationStrategy(profile=risk_profile)
        self.risk_engine = PortfolioRiskEngine()

    def allocate_single(
        self,
        recommendation_result: RecommendationResult,
        available_capital: float,
        risk_profile: Optional[RiskProfile] = None,
        sector: str = "General",
    ) -> PortfolioRecommendation:
        """
        Allocates capital for a single evaluated IPO opportunity.
        """
        return self.allocate_portfolio(
            recommendations=[(recommendation_result, sector)],
            available_capital=available_capital,
            risk_profile=risk_profile,
        )

    def allocate_portfolio(
        self,
        recommendations: List[Union[RecommendationResult, tuple]],
        available_capital: float,
        risk_profile: Optional[RiskProfile] = None,
    ) -> PortfolioRecommendation:
        """
        Allocates available capital across a cohort of IPO recommendations.
        :param recommendations: List of RecommendationResult objects or (RecommendationResult, sector_name) tuples.
        :param available_capital: Total portfolio liquidity available for deployment.
        :param risk_profile: Override risk profile (CONSERVATIVE, MODERATE, AGGRESSIVE).
        :return: PortfolioRecommendation containing detailed positions, risk scores, and analytics.
        """
        if available_capital < 0.0:
            raise ValueError(f"Available capital must be non-negative, got {available_capital}")

        profile = risk_profile or self.strategy.profile
        strategy = AllocationStrategy(profile=profile)
        diversification_notes: List[str] = []

        if available_capital == 0.0 or not recommendations:
            return PortfolioRecommendation(
                total_capital=available_capital,
                total_allocated_capital=0.0,
                unallocated_cash=available_capital,
                total_allocation_percentage=0.0,
                risk_profile=profile,
                allocations=[],
                sector_allocations={},
                portfolio_risk_score=0.0,
                concentration_risk=0.0,
                exposure_risk=0.0,
                portfolio_risk_category=PortfolioRiskCategory.LOW,
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_score=0.0,
                diversification_notes=["No opportunities available or zero investment capital provided."],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # 1. Normalize input list into (RecommendationResult, sector) tuples
        items = []
        for rec_item in recommendations:
            if isinstance(rec_item, tuple):
                rec, sector = rec_item
            else:
                rec = rec_item
                # When sector is not specified, treat as distinct / general
                sector = getattr(rec, "sector", getattr(rec, "company_name", "General"))
            items.append((rec, sector))

        # Sort recommendations by conviction: Composite score descending
        # Prioritize Strong Subscribe > Subscribe > Neutral
        items.sort(key=lambda x: x[0].composite_score, reverse=True)

        # 2. Compute Preliminary Desired Allocations
        preliminary_allocs = []
        for rec, sector in items:
            base_pct = strategy.get_base_allocation_pct(rec.recommendation)
            preliminary_allocs.append({
                "rec": rec,
                "sector": sector,
                "target_pct": base_pct,
            })

        # 3. Apply Diversification Constraints
        # Constraint A: Single position cap <= 35%
        for item in preliminary_allocs:
            if item["target_pct"] > strategy.max_single_ipo_pct:
                diversification_notes.append(
                    f"Position {item['rec'].company_name} capped at single-stock limit {strategy.max_single_ipo_pct}%."
                )
                item["target_pct"] = strategy.max_single_ipo_pct

        # Constraint B: Sector concentration cap <= 40%
        sector_accumulated = defaultdict(float)
        for item in preliminary_allocs:
            sec = item["sector"]
            current_sec_pct = sector_accumulated[sec]
            if current_sec_pct + item["target_pct"] > strategy.max_sector_concentration_pct:
                allowed_pct = max(0.0, strategy.max_sector_concentration_pct - current_sec_pct)
                if allowed_pct < item["target_pct"]:
                    diversification_notes.append(
                        f"Sector '{sec}' reached concentration ceiling ({strategy.max_sector_concentration_pct}%). "
                        f"Reduced {item['rec'].company_name} allocation from {item['target_pct']:.1f}% to {allowed_pct:.1f}%."
                    )
                    item["target_pct"] = allowed_pct
            sector_accumulated[sec] += item["target_pct"]

        # Constraint C: Total capital deployment cap <= 100%
        total_requested_pct = sum(item["target_pct"] for item in preliminary_allocs)
        if total_requested_pct > strategy.max_total_allocation_pct:
            # Pro-rata downscale active positive allocations to fit within 100%
            scale_factor = strategy.max_total_allocation_pct / total_requested_pct
            diversification_notes.append(
                f"Total requested allocation ({total_requested_pct:.1f}%) exceeded 100% capacity. "
                f"Pro-rata scaling factor {scale_factor:.3f} applied across all positions."
            )
            for item in preliminary_allocs:
                item["target_pct"] = round(item["target_pct"] * scale_factor, 4)

        # 4. Generate Final Capital Allocation Position Objects
        final_allocations: List[CapitalAllocation] = []
        final_sector_totals = defaultdict(float)

        for item in preliminary_allocs:
            rec = item["rec"]
            sector = item["sector"]
            alloc_pct = item["target_pct"]
            allocated_amt = (alloc_pct / 100.0) * available_capital

            # Estimate payoffs
            exp_ret, exp_risk = self.risk_engine.estimate_ipo_payoff_profile(
                recommendation=rec.recommendation,
                composite_score=rec.composite_score,
                risk_level=rec.risk_level,
            )

            # Portfolio weight relative to deployed capital (or total capital)
            port_weight = alloc_pct / 100.0

            rationale_text = (
                f"{rec.recommendation.value} ({rec.composite_score:.1f}/100) under {profile.value} profile: "
                f"Allocated {alloc_pct:.1f}% (Rs {allocated_amt:,.2f})."
            )
            if alloc_pct == 0.0:
                rationale_text = f"Zero allocation: {rec.recommendation.value} recommendation."

            pos = CapitalAllocation(
                ipo_id=rec.ipo_id,
                company_name=rec.company_name,
                sector=sector,
                recommendation=rec.recommendation,
                composite_score=rec.composite_score,
                allocated_amount=round(allocated_amt, 2),
                allocation_percentage=round(alloc_pct, 2),
                position_size=round(allocated_amt, 2),
                portfolio_weight=round(port_weight, 4),
                expected_return=exp_ret,
                expected_risk=exp_risk,
                risk_level=rec.risk_level,
                rationale=rationale_text,
            )
            final_allocations.append(pos)
            final_sector_totals[sector] += alloc_pct

        # 5. Aggregate Portfolio-Level Metrics
        total_allocated_capital = sum(a.allocated_amount for a in final_allocations)
        total_allocated_pct = sum(a.allocation_percentage for a in final_allocations)
        unallocated_cash = max(0.0, available_capital - total_allocated_capital)

        # 6. Portfolio Risk Calculations
        # Filter active positive allocations for risk calculations
        active_allocs = [a for a in final_allocations if a.allocated_amount > 0.0]

        concentration_risk = self.risk_engine.calculate_concentration_risk(
            allocations=active_allocs,
            total_allocated=total_allocated_capital,
        )
        exposure_risk = self.risk_engine.calculate_exposure_risk(
            total_allocated=total_allocated_capital,
            total_capital=available_capital,
        )
        portfolio_risk_score = self.risk_engine.calculate_portfolio_risk_score(
            allocations=active_allocs,
            concentration_risk=concentration_risk,
            exposure_risk=exposure_risk,
        )
        risk_category = self.risk_engine.assign_risk_category(portfolio_risk_score)

        # 7. Portfolio Payoff & Sharpe Analytics
        expected_ret, expected_risk, sharpe = self.risk_engine.calculate_portfolio_analytics(
            allocations=active_allocs,
            total_capital=available_capital,
            total_allocated=total_allocated_capital,
        )

        return PortfolioRecommendation(
            total_capital=round(available_capital, 2),
            total_allocated_capital=round(total_allocated_capital, 2),
            unallocated_cash=round(unallocated_cash, 2),
            total_allocation_percentage=round(total_allocated_pct, 2),
            risk_profile=profile,
            allocations=final_allocations,
            sector_allocations=dict(final_sector_totals),
            portfolio_risk_score=portfolio_risk_score,
            concentration_risk=concentration_risk,
            exposure_risk=exposure_risk,
            portfolio_risk_category=risk_category,
            expected_return=expected_ret,
            expected_risk=expected_risk,
            sharpe_score=sharpe,
            diversification_notes=diversification_notes,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
