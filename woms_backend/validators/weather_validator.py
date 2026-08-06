# =============================================================================
# SYNOP Validation Engine — Weather Validator
# =============================================================================
# Requirement §9: Validates present and past weather codes.
#   - Present weather ww (00–99, WMO Code Table 4677)
#   - Past weather W1, W2 (0–9, WMO Code Table 4561)
#   - W1 ≥ W2 (W1 should be the more significant past weather)
#   - Weather code compatibility (fog ↔ low visibility, etc.)
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    VALID_WW_CODES, VALID_W_CODES,
    WW_FOG, WW_PRECIPITATION, WW_NO_PRECIPITATION,
    W_DESCRIPTIONS,
)

logger = logging.getLogger(__name__)

DOMAIN = "weather"


def validate_weather(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate present and past weather observations.

    Expected keys: present_weather, past_weather_1, past_weather_2.

    Parameters
    ----------
    data : dict
        Observation data dictionary.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    ww_raw = data.get("present_weather")
    w1_raw = data.get("past_weather_1")
    w2_raw = data.get("past_weather_2")
    ix_raw = str(data.get("weather_indicator"))

    # ------------------------------------------------------------------
    # 0. Code Table 19 (iX) Mandatory Checks
    # ------------------------------------------------------------------
    if ix_raw in ["1", "4"]:
        if ww_raw is None or str(ww_raw).strip() == "":
            results.append(make_result(
                DOMAIN, "Mandatory Present Weather (iX=1,4)", ww_raw,
                "Required when iX is 1 or 4", "Missing",
                ValidationStatus.ERROR,
                f"Present weather is mandatory when station weather indicator (iX) is {ix_raw}.",
                "Enter a valid present weather code."
            ))
        if w1_raw is None or str(w1_raw).strip() == "":
            results.append(make_result(
                DOMAIN, "Mandatory Past Weather 1 (iX=1,4)", w1_raw,
                "Required when iX is 1 or 4", "Missing",
                ValidationStatus.ERROR,
                f"Past weather 1 is mandatory when station weather indicator (iX) is {ix_raw}.",
                "Enter a valid past weather code."
            ))
    elif ix_raw in ["2", "3", "5", "6"]:
        for label, val in [("Present weather (ww)", ww_raw), ("Past weather W1", w1_raw), ("Past weather W2", w2_raw)]:
            if val is not None and str(val).strip() != "":
                results.append(make_result(
                    DOMAIN, f"Omitted {label} (iX={ix_raw})", val,
                    "Must be omitted", str(val),
                    ValidationStatus.ERROR,
                    f"{label} must not be entered when station weather indicator (iX) is {ix_raw}.",
                    f"Remove the {label}."
                ))

    # ------------------------------------------------------------------
    # 1. Present weather ww
    # ------------------------------------------------------------------
    if ww_raw is not None:
        ww_val = _to_int(ww_raw)
        if ww_val is not None:
            if ww_val in VALID_WW_CODES:
                results.append(make_result(
                    DOMAIN, "Present Weather (ww)", ww_val,
                    "00–99", f"{ww_val:02d}",
                    ValidationStatus.PASS,
                    f"Present weather code {ww_val:02d} is valid."
                ))
            else:
                results.append(make_result(
                    DOMAIN, "Present Weather (ww)", ww_val,
                    "00–99", str(ww_val),
                    ValidationStatus.ERROR,
                    f"Present weather code {ww_val} is outside the valid "
                    "range (00–99).",
                    "Use a code from WMO Code Table 4677."
                ))
        else:
            results.append(make_result(
                DOMAIN, "Present Weather (ww)", ww_raw,
                "00–99 (numeric)", str(ww_raw),
                ValidationStatus.ERROR,
                f"Present weather '{ww_raw}' is not a valid integer.",
                "Use a numeric code from 00 to 99."
            ))

    # ------------------------------------------------------------------
    # 2. Past weather W1
    # ------------------------------------------------------------------
    w1_val = None
    if w1_raw is not None:
        w1_str = str(w1_raw)
        if w1_str in VALID_W_CODES:
            w1_val = _to_int(w1_raw)
            results.append(make_result(
                DOMAIN, "Past Weather W1", w1_str,
                "0–9 or /", w1_str,
                ValidationStatus.PASS,
                f"Past weather W1 code '{w1_str}' is valid."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Past Weather W1", w1_str,
                "0–9 or /", w1_str,
                ValidationStatus.ERROR,
                f"Past weather W1 code '{w1_str}' is invalid.",
                "Use WMO Code Table 4561 (values 0–9)."
            ))

    # ------------------------------------------------------------------
    # 3. Past weather W2
    # ------------------------------------------------------------------
    w2_val = None
    if w2_raw is not None:
        w2_str = str(w2_raw)
        if w2_str in VALID_W_CODES:
            w2_val = _to_int(w2_raw)
            results.append(make_result(
                DOMAIN, "Past Weather W2", w2_str,
                "0–9 or /", w2_str,
                ValidationStatus.PASS,
                f"Past weather W2 code '{w2_str}' is valid."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Past Weather W2", w2_str,
                "0–9 or /", w2_str,
                ValidationStatus.ERROR,
                f"Past weather W2 code '{w2_str}' is invalid.",
                "Use WMO Code Table 4561 (values 0–9)."
            ))

    # ------------------------------------------------------------------
    # 4. W1 ≥ W2 (W1 should represent more significant weather)
    # ------------------------------------------------------------------
    if w1_val is not None and w2_val is not None:
        if w1_val >= w2_val:
            results.append(make_result(
                DOMAIN, "W1 ≥ W2 (Significance)",
                f"W1={w1_val}, W2={w2_val}",
                "W1 ≥ W2 (W1 is the more significant past weather)",
                f"{w1_val} ≥ {w2_val}",
                ValidationStatus.PASS,
                "W1 correctly represents the more significant past weather."
            ))
        else:
            results.append(make_result(
                DOMAIN, "W1 ≥ W2 (Significance)",
                f"W1={w1_val}, W2={w2_val}",
                "W1 ≥ W2 (W1 is the more significant past weather)",
                f"{w1_val} < {w2_val}",
                ValidationStatus.WARNING,
                f"W1 ({w1_val}) is less significant than W2 ({w2_val}). "
                "WMO convention: W1 should be the more significant past weather.",
                "Swap W1 and W2 so the more significant event is W1."
            ))

    # ------------------------------------------------------------------
    # 5. Weather phenomena flags consistency
    # ------------------------------------------------------------------
    ww_val = _to_int(ww_raw) if ww_raw is not None else None

    # Thunder flag vs. ww code
    if data.get("phenomenon_thunder") and ww_val is not None:
        if ww_val < 91:  # thunderstorm codes are 91–99
            results.append(make_result(
                DOMAIN, "Thunder Flag vs. ww",
                f"Thunder=True, ww={ww_val}",
                "If thunder flagged, ww should be 91–99 or 13/17/29",
                f"ww={ww_val}",
                ValidationStatus.WARNING,
                f"Thunder phenomenon is flagged but present weather code "
                f"({ww_val}) does not indicate a thunderstorm (91–99).",
                "If thunder is occurring, consider using ww=91–99."
            ))

    # Fog flag vs. ww code
    if data.get("phenomenon_fog") and ww_val is not None:
        if ww_val not in WW_FOG and ww_val not in range(10, 13):
            results.append(make_result(
                DOMAIN, "Fog Flag vs. ww",
                f"Fog=True, ww={ww_val}",
                "If fog flagged, ww should be 40–49 or 10–12",
                f"ww={ww_val}",
                ValidationStatus.WARNING,
                f"Fog phenomenon is flagged but present weather code "
                f"({ww_val}) does not indicate fog.",
                "If fog is present, consider using ww=40–49."
            ))

    # Snow flag vs. ww code
    if data.get("phenomenon_snow") and ww_val is not None:
        snow_codes = set(range(70, 80)) | {85, 86}
        if ww_val not in snow_codes:
            results.append(make_result(
                DOMAIN, "Snow Flag vs. ww",
                f"Snow=True, ww={ww_val}",
                "If snow flagged, ww should be 70–79 or 85–86",
                f"ww={ww_val}",
                ValidationStatus.WARNING,
                f"Snow phenomenon is flagged but present weather code "
                f"({ww_val}) does not indicate snow.",
                "If snow is falling, consider using ww=70–79."
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
