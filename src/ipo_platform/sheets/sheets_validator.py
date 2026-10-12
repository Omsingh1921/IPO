"""
Tabular Validation Engine for Phase 2 Google Sheets Datastore.
Validates tab headers, prohibited field occurrences, mathematical formulas, and provenance links.
"""

from typing import Any, Dict, List, Tuple
from .sheets_schema import GOOGLE_SHEETS_TAB_HEADERS, SheetTabName
from ..engine.validators import PROHIBITED_FIELD_NAMES


class SheetsValidationError(Exception):
    """Raised when tabular Google Sheets data violates schema contracts."""

    pass


class SheetsTabularValidator:
    """Validates header structures, row data integrity, and compliance across 11 tabs."""

    @staticmethod
    def validate_headers(tab_name: SheetTabName, headers: List[str]) -> Tuple[bool, List[str]]:
        """Verifies that tab headers strictly match documented schema headers."""
        errors = []
        expected_headers = GOOGLE_SHEETS_TAB_HEADERS.get(tab_name, [])
        missing = [h for h in expected_headers if h not in headers]
        if missing:
            errors.append(f"Tab '{tab_name.value}' is missing required headers: {missing}")

        for h in headers:
            if h in PROHIBITED_FIELD_NAMES:
                errors.append(f"Tab '{tab_name.value}' contains prohibited header '{h}'.")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_master_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates IPO_Master tab row."""
        errors = []
        if not row.get("ipo_id"):
            errors.append("IPO_Master row missing 'ipo_id'.")
        if not row.get("company_name"):
            errors.append("IPO_Master row missing 'company_name'.")
        if row.get("segment") not in ["Mainboard", "SME"]:
            errors.append(f"Invalid segment '{row.get('segment')}'. Must be Mainboard or SME.")
        return (len(errors) == 0, errors)

    @staticmethod
    def validate_scenario_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates Scenarios tab row math: target_price_40 == reference_price * 1.40."""
        errors = []
        ref_price = row.get("reference_price")
        target_40 = row.get("target_price_40")
        req_move = row.get("required_move")

        if ref_price is not None and target_40 is not None:
            try:
                ref_f = float(ref_price)
                target_f = float(target_40)
                expected_t = round(ref_f * 1.40, 2)
                if abs(target_f - expected_t) > 0.01:
                    errors.append(
                        f"Scenarios tab math error: target_price_40 ({target_f}) != reference_price * 1.40 ({expected_t})."
                    )
            except (ValueError, TypeError):
                errors.append("Scenarios tab numerical parsing error.")

        if req_move is not None:
            try:
                if abs(float(req_move) - 40.00) > 0.001:
                    errors.append(f"Scenarios tab required_move ({req_move}) must strictly equal 40.00.")
            except (ValueError, TypeError):
                errors.append("Scenarios tab required_move parsing error.")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_gmp_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates GMP tab row governance rules."""
        errors = []
        source_type = row.get("source_type")
        if source_type and source_type != "Unofficial GMP":
            errors.append(f"GMP tab source_type must strictly equal 'Unofficial GMP', got '{source_type}'.")
        return (len(errors) == 0, errors)
