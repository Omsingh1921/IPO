"""
The 40% Target Scenario Evaluation Module for Indian IPO Research Platform.
Evaluates conditional +40% listing scenario hypotheses adhering strictly to non-predictive governance rules.
"""

from typing import List, Optional
from ..models.schema import Scenario40Percent
from ..models.enums import ScenarioStatusEnum


class Scenario40PercentEvaluator:
    """Evaluates and builds Scenario40Percent objects adhering strictly to schema rules."""

    STANDARD_METHODOLOGY_DISCLAIMER = (
        "Standardized non-predictive scenario model evaluating plausibility of +40% move."
    )

    @classmethod
    def create_scenario(
        cls,
        reference_price: float,
        reference_eps: Optional[float] = None,
        reference_book_value_per_share: Optional[float] = None,
        supporting_factors: Optional[List[str]] = None,
        contradictory_factors: Optional[List[str]] = None,
        timestamp: str = "",
    ) -> Scenario40Percent:
        """Constructs a standard Scenario40Percent instance with strict formula enforcement."""
        if reference_price <= 0:
            raise ValueError("Reference price must be strictly positive.")

        target_price = round(reference_price * 1.40, 2)
        required_move = 40.00

        target_pe = None
        if reference_eps and reference_eps > 0:
            target_pe = round(target_price / reference_eps, 2)

        target_pb = None
        if reference_book_value_per_share and reference_book_value_per_share > 0:
            target_pb = round(target_price / reference_book_value_per_share, 2)

        supp_list = supporting_factors if supporting_factors is not None else []
        contra_list = contradictory_factors if contradictory_factors is not None else []

        # Determine scenario status based on objective factor balance
        if len(supp_list) > len(contra_list) and len(supp_list) >= 2:
            status = ScenarioStatusEnum.SUPPORTED
        elif len(contra_list) > len(supp_list) and len(contra_list) >= 2:
            status = ScenarioStatusEnum.NOT_SUPPORTED
        else:
            status = ScenarioStatusEnum.INSUFFICIENT_EVIDENCE

        return Scenario40Percent(
            reference_price=reference_price,
            target_price=target_price,
            required_price_movement=required_move,
            target_pe=target_pe,
            target_pb=target_pb,
            supporting_factors=supp_list,
            contradictory_factors=contra_list,
            scenario_status=status,
            scenario_methodology=cls.STANDARD_METHODOLOGY_DISCLAIMER,
            scenario_data_timestamp=timestamp,
        )
