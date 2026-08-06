# =============================================================================
# SYNOP Validation Engine — Visibility Validator
# =============================================================================
# Requirement §7: Validates visibility observations.
#   - VV code validation (00–89 standard, 90–99 special)
#   - Decodes visibility value from VV code
#   - Detects invalid/reserved codes
#   - Validates raw visibility value from observation data
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import VV_RESERVED, VV_SPECIAL

logger = logging.getLogger(__name__)

DOMAIN = "visibility"


def validate_visibility(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate visibility observations from the observation data dictionary.

    Expected keys: visibility, visibility_unit.

    Parameters
    ----------
    data : dict
        Observation data dictionary.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    vis_raw = data.get("visibility")
    vis_unit = data.get("visibility_unit")

    if vis_raw is None:
        results.append(make_result(
            DOMAIN, "Visibility Presence", None,
            "Visibility should be reported",
            None, ValidationStatus.WARNING,
            "Visibility observation is missing.",
            "Report the horizontal visibility."
        ))
        return results

    vis_val = _to_float(vis_raw)
    if vis_val is None:
        results.append(make_result(
            DOMAIN, "Visibility Numeric", vis_raw,
            "Numeric value", str(vis_raw),
            ValidationStatus.ERROR,
            f"Visibility value '{vis_raw}' is not a valid number.",
            "Enter a numeric visibility value."
        ))
        return results

    # Convert to km for validation
    vis_km = vis_val
    if vis_unit == "meters":
        vis_km = vis_val / 1000.0

    # ------------------------------------------------------------------
    # 1. Non-negative check
    # ------------------------------------------------------------------
    if vis_km < 0:
        results.append(make_result(
            DOMAIN, "Visibility Range", vis_val,
            "≥ 0", f"{vis_km} km",
            ValidationStatus.ERROR,
            "Visibility cannot be negative.",
            "Enter a non-negative visibility value."
        ))
        return results

    # ------------------------------------------------------------------
    # 2. Upper bound reasonableness
    # ------------------------------------------------------------------
    if vis_km > 100.0:
        results.append(make_result(
            DOMAIN, "Visibility Upper Bound", vis_val,
            "≤ 100 km (practical limit)", f"{vis_km} km",
            ValidationStatus.WARNING,
            f"Visibility ({vis_km} km) exceeds the normal observable range. "
            "The maximum VV code (99) represents ≥ 50 km.",
            "Verify the visibility estimate. Cap at 70 km for coding."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Visibility Range", vis_val,
            "0–100 km", f"{vis_km} km",
            ValidationStatus.PASS,
            f"Visibility ({vis_km} km) is within the valid range."
        ))

    # ------------------------------------------------------------------
    # 3. Determine the VV code that would be encoded and validate it
    # ------------------------------------------------------------------
    vv_code = _encode_vv(vis_km)
    if vv_code is not None:
        if vv_code in VV_RESERVED:
            results.append(make_result(
                DOMAIN, "VV Code Reserved Check", vv_code,
                "VV codes 51–55 are reserved", str(vv_code),
                ValidationStatus.WARNING,
                f"Encoded VV code {vv_code} falls in the reserved range (51–55).",
                "Check visibility value; this range is not normally used."
            ))
        else:
            results.append(make_result(
                DOMAIN, "VV Code Validity", vv_code,
                "00–50, 56–99", str(vv_code),
                ValidationStatus.PASS,
                f"Encoded VV code ({vv_code:02d}) is valid."
            ))

    return results


def validate_vv_code(vv_str: str) -> List[ValidationResult]:
    """
    Validate a VV code extracted from a SYNOP string.

    Parameters
    ----------
    vv_str : str
        Two-character VV code (e.g. "56", "//").

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    if vv_str == "//":
        results.append(make_result(
            DOMAIN, "VV Code", vv_str, "00–99 or //",
            vv_str, ValidationStatus.WARNING,
            "Visibility code is missing (//).",
            "Report visibility if observable."
        ))
        return results

    if not vv_str.isdigit():
        results.append(make_result(
            DOMAIN, "VV Code", vv_str, "00–99 (numeric)",
            vv_str, ValidationStatus.ERROR,
            f"VV code '{vv_str}' is not numeric.",
        ))
        return results

    vv = int(vv_str)

    if vv in VV_RESERVED:
        results.append(make_result(
            DOMAIN, "VV Code Reserved", vv_str,
            "Codes 51–55 are reserved",
            str(vv), ValidationStatus.WARNING,
            f"VV code {vv} is in the reserved range (51–55).",
            "Use codes 00–50 or 56–99."
        ))
    elif 0 <= vv <= 99:
        decoded = _decode_vv(vv)
        results.append(make_result(
            DOMAIN, "VV Code Valid", vv_str,
            "00–99", f"{vv} → {decoded}",
            ValidationStatus.PASS,
            f"VV code {vv:02d} is valid (visibility: {decoded})."
        ))
    else:
        results.append(make_result(
            DOMAIN, "VV Code Range", vv_str,
            "00–99", str(vv), ValidationStatus.ERROR,
            f"VV code {vv} is outside the valid range (00–99).",
        ))

    return results


# -----------------------------------------------------------------------
# Encoding / decoding helpers
# -----------------------------------------------------------------------

def _encode_vv(vis_km: float) -> Optional[int]:
    """Encode visibility in km to VV code per WMO FM-12."""
    if vis_km < 0.1:
        return 0
    elif vis_km <= 5.0:
        return int(round(vis_km * 10))
    elif vis_km <= 30.0:
        return int(round(vis_km + 50))
    elif vis_km <= 70.0:
        return int(round((vis_km - 30) / 5 + 80))
    else:
        return 89


def _decode_vv(vv: int) -> str:
    """Decode VV code to human-readable visibility string."""
    if vv == 0:
        return "< 0.1 km"
    elif 1 <= vv <= 50:
        return f"{vv / 10:.1f} km"
    elif 56 <= vv <= 80:
        return f"{vv - 50} km"
    elif 81 <= vv <= 88:
        return f"{35 + (vv - 80) * 5} km"
    elif vv == 89:
        return "> 70 km"
    elif vv in VV_SPECIAL:
        return VV_SPECIAL[vv]
    else:
        return f"Code {vv}"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
