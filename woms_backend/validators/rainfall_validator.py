# =============================================================================
# SYNOP Validation Engine — Rainfall Validator
# =============================================================================
# Requirement §10: Validates rainfall observations.
#   - RRR code: 000–999 or ///
#   - Trace rainfall code: 990
#   - Duration tR code: 1–9 (Code Table 3590)
#   - Impossible values: rainfall > 500 mm in single period
#   - Consistency: no-precip weather + rainfall > 0 → WARNING
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    VALID_TR_CODES, MAX_RAINFALL_SINGLE_PERIOD, MAX_RAINFALL_24H,
    WW_NO_PRECIPITATION,
)

logger = logging.getLogger(__name__)

DOMAIN = "rainfall"


def validate_rainfall(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate rainfall observations.

    Expected keys: rainfall, rain_duration, rainfall_24h, present_weather.

    Parameters
    ----------
    data : dict
        Observation data dictionary.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    rain_raw = data.get("rainfall")
    rain_dur = data.get("rain_duration")
    rain_24h = _to_float(data.get("rainfall_24h"))
    ww_val = _to_int(data.get("present_weather"))
    ir_val = str(data.get("precipitation_indicator"))

    # ------------------------------------------------------------------
    # 0. Code Table 17 (iR) Mandatory Checks
    # ------------------------------------------------------------------
    if ir_val in ["1", "2"]:
        if rain_raw is None or str(rain_raw).strip() == "":
            results.append(make_result(
                DOMAIN, "Mandatory Rainfall (iR=1,2)", rain_raw,
                "Required when iR is 1 or 2", "Missing",
                ValidationStatus.ERROR,
                f"Rainfall amount is mandatory when precipitation indicator (iR) is {ir_val}.",
                "Enter a valid rainfall amount."
            ))
        if rain_dur is None or str(rain_dur).strip() == "":
            results.append(make_result(
                DOMAIN, "Mandatory Rain Duration (iR=1,2)", rain_dur,
                "Required when iR is 1 or 2", "Missing",
                ValidationStatus.ERROR,
                f"Rain duration is mandatory when precipitation indicator (iR) is {ir_val}.",
                "Enter a valid rain duration code."
            ))
    elif ir_val == "3":
        if rain_raw is None or str(rain_raw).strip() == "":
            results.append(make_result(
                DOMAIN, "Rainfall Amount (iR=3)", rain_raw,
                "0 mm", "Missing",
                ValidationStatus.ERROR,
                "Rainfall amount must be 0 when precipitation indicator (iR) is 3.",
                "Enter 0 for rainfall."
            ))
        else:
            rain_float = _to_float(rain_raw)
            if rain_float != 0.0:
                results.append(make_result(
                    DOMAIN, "Rainfall Amount (iR=3)", rain_raw,
                    "0 mm", f"{rain_float} mm",
                    ValidationStatus.ERROR,
                    "Rainfall amount must be 0 when precipitation indicator (iR) is 3.",
                    "Set rainfall amount to 0."
                ))
    elif ir_val == "4":
        if rain_raw is not None and str(rain_raw).strip() != "":
            results.append(make_result(
                DOMAIN, "Rainfall Amount (iR=4)", rain_raw,
                "Must be omitted", str(rain_raw),
                ValidationStatus.ERROR,
                "Rainfall amount must not be entered when precipitation indicator (iR) is 4.",
                "Remove the rainfall amount."
            ))

    # ------------------------------------------------------------------
    # 1. Rainfall amount — basic checks
    # ------------------------------------------------------------------
    if rain_raw is not None:
        rain_val = _to_float(rain_raw)

        if rain_val is None:
            results.append(make_result(
                DOMAIN, "Rainfall Numeric", rain_raw,
                "Numeric value", str(rain_raw),
                ValidationStatus.ERROR,
                f"Rainfall value '{rain_raw}' is not a valid number.",
                "Enter a numeric rainfall amount in mm."
            ))
        elif rain_val < 0:
            results.append(make_result(
                DOMAIN, "Rainfall Non-Negative", rain_val,
                "≥ 0 mm", f"{rain_val} mm",
                ValidationStatus.ERROR,
                "Rainfall cannot be negative.",
                "Enter 0 for no precipitation or a positive amount."
            ))
        elif rain_val > MAX_RAINFALL_SINGLE_PERIOD:
            results.append(make_result(
                DOMAIN, "Rainfall Extreme Check", rain_val,
                f"≤ {MAX_RAINFALL_SINGLE_PERIOD} mm (single period)",
                f"{rain_val} mm",
                ValidationStatus.ERROR,
                f"Rainfall ({rain_val} mm) exceeds the extreme threshold "
                f"of {MAX_RAINFALL_SINGLE_PERIOD} mm for a single period.",
                "Verify the rain gauge reading."
            ))
        elif rain_val > 200:
            results.append(make_result(
                DOMAIN, "Rainfall High Value", rain_val,
                "≤ 200 mm (normal range)", f"{rain_val} mm",
                ValidationStatus.WARNING,
                f"Rainfall ({rain_val} mm) is unusually high. "
                "This is possible in extreme events but should be verified.",
                "Double-check the rain gauge."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Rainfall Amount", rain_val,
                f"0–{MAX_RAINFALL_SINGLE_PERIOD} mm",
                f"{rain_val} mm",
                ValidationStatus.PASS,
                f"Rainfall amount ({rain_val} mm) is within range."
            ))

        # Trace rainfall detection
        if rain_val is not None and 0 < rain_val <= 0.05:
            results.append(make_result(
                DOMAIN, "Trace Rainfall", rain_val,
                "Trace → encoded as RRR=990",
                f"{rain_val} mm",
                ValidationStatus.PASS,
                "Trace rainfall detected (≤ 0.05 mm). "
                "This will be encoded as RRR=990."
            ))

        # ------------------------------------------------------------------
        # 2. Consistency: no-precip weather but rainfall > 0
        # ------------------------------------------------------------------
        if rain_val is not None and rain_val > 0 and ww_val is not None:
            if ww_val in WW_NO_PRECIPITATION:
                results.append(make_result(
                    DOMAIN, "Weather vs. Rainfall Consistency",
                    f"ww={ww_val}, rain={rain_val}",
                    "If ww=00–03 (no significant weather), rainfall should be 0",
                    f"ww={ww_val}, rain={rain_val} mm",
                    ValidationStatus.WARNING,
                    f"Present weather ({ww_val}) indicates no significant "
                    f"weather, but rainfall is {rain_val} mm.",
                    "If precipitation occurred, update the present weather code."
                ))

    # ------------------------------------------------------------------
    # 3. Rain duration tR code
    # ------------------------------------------------------------------
    if rain_dur is not None:
        dur_str = str(rain_dur)
        if dur_str in VALID_TR_CODES:
            results.append(make_result(
                DOMAIN, "Rain Duration Code (tR)", dur_str,
                "1–9 or /", dur_str,
                ValidationStatus.PASS,
                f"Rain duration code '{dur_str}' is valid."
            ))
        elif dur_str == "/":
            results.append(make_result(
                DOMAIN, "Rain Duration Code (tR)", dur_str,
                "1–9 or /", dur_str,
                ValidationStatus.WARNING,
                "Rain duration is unknown (/).",
                "Report the precipitation accumulation period."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Rain Duration Code (tR)", dur_str,
                "1–9 or /", dur_str,
                ValidationStatus.ERROR,
                f"Rain duration code '{dur_str}' is invalid.",
                "Use WMO Code Table 3590 (1=6h, 2=12h, 3=18h, 4=24h, etc.)."
            ))

    # ------------------------------------------------------------------
    # 4. 24-hour rainfall (Section 333)
    # ------------------------------------------------------------------
    if rain_24h is not None:
        if rain_24h < 0:
            results.append(make_result(
                DOMAIN, "24h Rainfall Non-Negative", rain_24h,
                "≥ 0 mm", f"{rain_24h} mm",
                ValidationStatus.ERROR,
                "24-hour rainfall cannot be negative.",
            ))
        elif rain_24h > MAX_RAINFALL_24H:
            results.append(make_result(
                DOMAIN, "24h Rainfall Extreme", rain_24h,
                f"≤ {MAX_RAINFALL_24H} mm", f"{rain_24h} mm",
                ValidationStatus.ERROR,
                f"24-hour rainfall ({rain_24h} mm) exceeds the extreme "
                f"threshold ({MAX_RAINFALL_24H} mm).",
                "Verify the 24-hour accumulated rainfall."
            ))
        else:
            results.append(make_result(
                DOMAIN, "24h Rainfall", rain_24h,
                f"0–{MAX_RAINFALL_24H} mm", f"{rain_24h} mm",
                ValidationStatus.PASS,
                f"24-hour rainfall ({rain_24h} mm) is within range."
            ))

    return results


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
