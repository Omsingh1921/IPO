"""
Validation engine for Indian IPO Research Platform.
Enforces business rules, prohibited field checks, math consistency, and provenance contracts.
"""

from typing import Any, Dict, List, Tuple
from ..models.schema import MasterIPORecord, Scenario40Percent
from ..models.enums import ScenarioStatusEnum

PROHIBITED_FIELD_NAMES = {
    "recommendation",
    "buy_signal",
    "sell_signal",
    "rating",
    "target_score",
    "rank",
    "score",
    "best_ipo",
    "anchor_quality_score",
    "anchor_quality",
    "anchor_strength",
    "anchor_rating",
    "probability_of_40_percent",
    "guaranteed_return",
    "expected_return",
    "gmp_signal",
    "gmp_buy_score",
}


class SchemaValidationError(Exception):
    """Raised when an IPO record violates schema contracts or governance rules."""

    pass


class IPOValidator:
    """Validates MasterIPORecord instances and dictionary representations."""

    @staticmethod
    def validate_prohibited_keys(raw_dict: Dict[str, Any], path: str = "") -> List[str]:
        """Recursively scans a dictionary to ensure forbidden fields do not exist."""
        violations = []
        for key, value in raw_dict.items():
            current_path = f"{path}.{key}" if path else key
            if key in PROHIBITED_FIELD_NAMES:
                violations.append(f"Prohibited field '{current_path}' found in dataset.")
            if isinstance(value, dict):
                violations.extend(IPOValidator.validate_prohibited_keys(value, current_path))
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        violations.extend(
                            IPOValidator.validate_prohibited_keys(item, f"{current_path}[{idx}]")
                        )
        return violations

    @staticmethod
    def validate_scenario_math(scenario: Scenario40Percent) -> Tuple[bool, List[str]]:
        """Enforces +40% target mathematical relationship rules:

        target_price == reference_price * 1.40
        required_price_movement == 40.00
        """
        errors = []
        expected_target = round(scenario.reference_price * 1.40, 4)
        actual_target = round(scenario.target_price, 4)

        if abs(expected_target - actual_target) > 0.01:
            errors.append(
                f"Invalid target price: {scenario.target_price}. "
                f"Target price must strictly equal reference_price * 1.40 ({expected_target})."
            )

        if abs(scenario.required_price_movement - 40.00) > 0.001:
            errors.append(
                f"Invalid required_price_movement: {scenario.required_price_movement}. Must strictly equal 40.00."
            )

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_record(record: MasterIPORecord) -> Tuple[bool, List[str]]:
        """Full validation sweep across a MasterIPORecord."""
        errors = []

        # 1. Prohibited keys check
        dict_rep = record.to_dict()
        prohibited_errors = IPOValidator.validate_prohibited_keys(dict_rep)
        errors.extend(prohibited_errors)

        # 2. Scenario 40% math check
        _, scenario_errors = IPOValidator.validate_scenario_math(record.scenario_40_percent)
        errors.extend(scenario_errors)

        # 3. Segment check
        if record.ipo_entity.segment.value not in ["Mainboard", "SME"]:
            errors.append(f"Invalid segment: '{record.ipo_entity.segment}'. Must be Mainboard or SME.")

        # 4. Pre-listing temporal separation check
        if record.ipo_status.listing_status.value == "Pre-Listing":
            if record.historical_ipo and record.historical_ipo.historical_ipo:
                errors.append(
                    "Temporal separation violation: Pre-Listing record flagged historical_ipo=True."
                )

        return (len(errors) == 0, errors)
