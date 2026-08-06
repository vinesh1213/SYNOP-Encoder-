# =============================================================================
# SYNOP Validation Engine — Cloud Validator
# =============================================================================
# Requirement §8: Validates cloud observations.
#   - Total cloud amount N (0–9 or /)
#   - Low cloud amount Nh (0–9 or /); must be ≤ N
#   - CL, CM, CH codes vs. WMO code tables
#   - Cloud base height h code
#   - Logical: N=0 → cloud types should be 0 or /
#   - Logical: N=9 (sky obscured) → CL=CM=CH=/
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    VALID_N_CODES, VALID_NH_CODES,
    VALID_CL_CODES, VALID_CM_CODES, VALID_CH_CODES,
    VALID_H_CODES,
)

logger = logging.getLogger(__name__)

DOMAIN = "clouds"


def validate_clouds(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate cloud observations.

    Expected keys: total_cloud_cover, low_cloud_amount, low_cloud_type,
    middle_cloud_type, high_cloud_type, lowest_cloud_base.

    Parameters
    ----------
    data : dict
        Observation data dictionary.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    n_raw = data.get("total_cloud_cover")
    nh_raw = data.get("low_cloud_amount")
    cl_raw = data.get("low_cloud_type")
    cm_raw = data.get("middle_cloud_type")
    ch_raw = data.get("high_cloud_type")
    h_raw = data.get("lowest_cloud_base")

    # ------------------------------------------------------------------
    # 1. Total cloud cover N
    # ------------------------------------------------------------------
    n_val = _to_int(n_raw)
    if n_val is not None:
        if 0 <= n_val <= 9:
            results.append(make_result(
                DOMAIN, "Total Cloud Cover (N)", n_val,
                "0–9 oktas", str(n_val),
                ValidationStatus.PASS,
                f"Total cloud cover: {n_val} oktas (or 9 for sky obscured)."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Total Cloud Cover (N)", n_val,
                "0–9 oktas", str(n_val),
                ValidationStatus.ERROR,
                f"Total cloud cover ({n_val}) is out of range (0–9 oktas).",
                "Use 0 for clear, 8 for overcast, 9 for obscured."
            ))
    elif n_raw is not None:
        n_str = str(n_raw)
        if n_str == "/":
            results.append(make_result(
                DOMAIN, "Total Cloud Cover (N)", n_str,
                "0–9 or /", n_str,
                ValidationStatus.WARNING,
                "Total cloud cover not observed (/).",
                "Report cloud cover if sky is visible."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Total Cloud Cover (N)", n_str,
                "0–9 or /", n_str,
                ValidationStatus.ERROR,
                f"Total cloud cover '{n_str}' is invalid.",
                "Use 0–9 (oktas) or '/' if not observable."
            ))

    # ------------------------------------------------------------------
    # 2. Low cloud amount Nh
    # ------------------------------------------------------------------
    nh_val = _to_int(nh_raw)
    if nh_val is not None:
        if 0 <= nh_val <= 9:
            results.append(make_result(
                DOMAIN, "Low Cloud Amount (Nh)", nh_val,
                "0–9 oktas", str(nh_val),
                ValidationStatus.PASS,
                f"Low cloud amount: {nh_val} oktas."
            ))

            # Nh ≤ N check
            if n_val is not None and nh_val > n_val and n_val != 9:
                results.append(make_result(
                    DOMAIN, "Nh ≤ N Check",
                    f"Nh={nh_val}, N={n_val}",
                    "Low cloud amount ≤ Total cloud cover",
                    f"{nh_val} > {n_val}",
                    ValidationStatus.ERROR,
                    f"Low cloud amount ({nh_val} oktas) exceeds total cloud "
                    f"cover ({n_val} oktas).",
                    "Low cloud amount cannot exceed total cloud cover."
                ))
            elif n_val is not None:
                results.append(make_result(
                    DOMAIN, "Nh ≤ N Check",
                    f"Nh={nh_val}, N={n_val}",
                    "Low cloud amount ≤ Total cloud cover",
                    f"{nh_val} ≤ {n_val}",
                    ValidationStatus.PASS,
                    "Low cloud amount is correctly ≤ total cloud cover."
                ))
        else:
            results.append(make_result(
                DOMAIN, "Low Cloud Amount (Nh)", nh_val,
                "0–9 oktas", str(nh_val),
                ValidationStatus.ERROR,
                f"Low cloud amount ({nh_val}) is out of range.",
            ))

    # ------------------------------------------------------------------
    # 3. Cloud types CL, CM, CH
    # ------------------------------------------------------------------
    for label, raw_val, valid_codes in [
        ("Low Cloud Type (CL)", cl_raw, VALID_CL_CODES),
        ("Middle Cloud Type (CM)", cm_raw, VALID_CM_CODES),
        ("High Cloud Type (CH)", ch_raw, VALID_CH_CODES),
    ]:
        if raw_val is not None:
            code = str(raw_val)
            if code in valid_codes:
                results.append(make_result(
                    DOMAIN, label, code,
                    "0–9 or /", code,
                    ValidationStatus.PASS,
                    f"{label}: code {code} is valid."
                ))
            else:
                results.append(make_result(
                    DOMAIN, label, code,
                    "0–9 or /", code,
                    ValidationStatus.ERROR,
                    f"{label} code '{code}' is not in the WMO code table.",
                    "Use WMO code table values 0–9 or '/'."
                ))

    # ------------------------------------------------------------------
    # 4. Cloud base height h
    # ------------------------------------------------------------------
    if h_raw is not None:
        h_val = _to_float(h_raw)
        if h_val is not None and h_val >= 0:
            results.append(make_result(
                DOMAIN, "Cloud Base Height", h_val,
                "≥ 0 meters", f"{h_val} m",
                ValidationStatus.PASS,
                f"Cloud base height: {h_val} m."
            ))
        elif h_val is not None:
            results.append(make_result(
                DOMAIN, "Cloud Base Height", h_val,
                "≥ 0 meters", f"{h_val} m",
                ValidationStatus.ERROR,
                "Cloud base height cannot be negative.",
            ))

    # ------------------------------------------------------------------
    # 5. Logical: N=0 → no cloud types
    # ------------------------------------------------------------------
    if n_val is not None and n_val == 0:
        for label, raw_val in [
            ("CL", cl_raw), ("CM", cm_raw), ("CH", ch_raw)
        ]:
            if raw_val is not None:
                code = str(raw_val)
                if code not in ("0", "/"):
                    results.append(make_result(
                        DOMAIN, f"N=0 but {label} ≠ 0",
                        f"N={n_val}, {label}={code}",
                        f"If N=0 (clear), {label} should be 0 or /",
                        code,
                        ValidationStatus.WARNING,
                        f"Sky is clear (N=0) but {label}={code}. "
                        f"With no clouds, {label} should be 0 or /.",
                        f"Set {label} to 0 or /."
                    ))

    # ------------------------------------------------------------------
    # 6. Logical: N=9 (sky obscured) → CL=CM=CH=/
    # ------------------------------------------------------------------
    if n_val is not None and n_val == 9:
        for label, raw_val in [
            ("CL", cl_raw), ("CM", cm_raw), ("CH", ch_raw)
        ]:
            if raw_val is not None:
                code = str(raw_val)
                if code != "/":
                    results.append(make_result(
                        DOMAIN, f"N=9 but {label} ≠ /",
                        f"N={n_val}, {label}={code}",
                        f"If N=9 (sky obscured), {label} should be /",
                        code,
                        ValidationStatus.WARNING,
                        f"Sky is obscured (N=9) but {label}={code}. "
                        f"When sky is obscured, cloud types are not observable.",
                        f"Set {label} to /."
                    ))

    return results


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
