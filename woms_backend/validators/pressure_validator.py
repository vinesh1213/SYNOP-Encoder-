# =============================================================================
# SYNOP Validation Engine — Pressure Validator
# =============================================================================
# Requirement §5: Validates pressure observations.
#   - Station pressure range (500–1100 hPa)
#   - Sea-level pressure range (870–1084 hPa)
#   - MSL pressure ≥ Station pressure (above sea level)
#   - Pressure tendency consistency (5appp)
#   - Abnormal pressure change detection
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    STATION_PRESSURE_MIN, STATION_PRESSURE_MAX,
    MSL_PRESSURE_MIN, MSL_PRESSURE_MAX,
    VALID_A_CODES, A_RISING, A_FALLING, A_STEADY,
)

logger = logging.getLogger(__name__)

DOMAIN = "pressure"


def validate_pressure(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate all pressure-related observations.

    Expected keys: station_pressure, msl_pressure, pressure_tendency,
    pressure_change.

    Parameters
    ----------
    data : dict
        Observation data dictionary.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    station_p = _to_float(data.get("station_pressure"))
    msl_p = _to_float(data.get("msl_pressure"))
    tendency = data.get("pressure_tendency")
    change = _to_float(data.get("pressure_change"))

    # ------------------------------------------------------------------
    # 1. Station Pressure — range check
    # ------------------------------------------------------------------
    if station_p is not None:
        if STATION_PRESSURE_MIN <= station_p <= STATION_PRESSURE_MAX:
            results.append(make_result(
                DOMAIN, "Station Pressure Range", station_p,
                f"{STATION_PRESSURE_MIN}–{STATION_PRESSURE_MAX} hPa",
                f"{station_p} hPa", ValidationStatus.PASS,
                f"Station pressure ({station_p} hPa) is within range."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Station Pressure Range", station_p,
                f"{STATION_PRESSURE_MIN}–{STATION_PRESSURE_MAX} hPa",
                f"{station_p} hPa", ValidationStatus.ERROR,
                f"Station pressure ({station_p} hPa) is outside the "
                f"acceptable range ({STATION_PRESSURE_MIN}–{STATION_PRESSURE_MAX} hPa).",
                "Verify the barometer reading and station elevation."
            ))
    else:
        results.append(make_result(
            DOMAIN, "Station Pressure Presence", None,
            "Station pressure should be reported",
            None, ValidationStatus.WARNING,
            "Station pressure is missing.",
            "Record the barometric station-level pressure."
        ))

    # ------------------------------------------------------------------
    # 2. Sea-Level (MSL) Pressure — range check
    # ------------------------------------------------------------------
    if msl_p is not None:
        if MSL_PRESSURE_MIN <= msl_p <= MSL_PRESSURE_MAX:
            results.append(make_result(
                DOMAIN, "MSL Pressure Range", msl_p,
                f"{MSL_PRESSURE_MIN}–{MSL_PRESSURE_MAX} hPa",
                f"{msl_p} hPa", ValidationStatus.PASS,
                f"MSL pressure ({msl_p} hPa) is within range."
            ))
        else:
            results.append(make_result(
                DOMAIN, "MSL Pressure Range", msl_p,
                f"{MSL_PRESSURE_MIN}–{MSL_PRESSURE_MAX} hPa",
                f"{msl_p} hPa", ValidationStatus.ERROR,
                f"MSL pressure ({msl_p} hPa) is outside the acceptable "
                f"range ({MSL_PRESSURE_MIN}–{MSL_PRESSURE_MAX} hPa).",
                "Verify the MSL pressure reduction calculation."
            ))

    # ------------------------------------------------------------------
    # 3. MSL ≥ Station Pressure (for stations above sea level)
    # ------------------------------------------------------------------
    if station_p is not None and msl_p is not None:
        if msl_p >= station_p:
            results.append(make_result(
                DOMAIN, "MSL ≥ Station Pressure",
                f"MSL={msl_p}, Station={station_p}",
                "MSL pressure ≥ Station pressure (above sea level)",
                f"{msl_p} ≥ {station_p}", ValidationStatus.PASS,
                "MSL pressure is correctly ≥ station pressure."
            ))
        else:
            diff = round(station_p - msl_p, 1)
            results.append(make_result(
                DOMAIN, "MSL ≥ Station Pressure",
                f"MSL={msl_p}, Station={station_p}",
                "MSL pressure ≥ Station pressure (above sea level)",
                f"{msl_p} < {station_p} (diff={diff} hPa)",
                ValidationStatus.WARNING,
                f"MSL pressure ({msl_p} hPa) is less than station pressure "
                f"({station_p} hPa). This is normal only for stations below "
                "sea level.",
                "Verify station elevation and pressure reduction formula."
            ))

    # ------------------------------------------------------------------
    # 4. Pressure tendency code (a) validation
    # ------------------------------------------------------------------
    if tendency is not None:
        tendency_str = str(tendency)
        if tendency_str in VALID_A_CODES:
            results.append(make_result(
                DOMAIN, "Pressure Tendency Code", tendency_str,
                "0–8", tendency_str, ValidationStatus.PASS,
                f"Pressure tendency code '{tendency_str}' is valid."
            ))
        elif tendency_str == "/":
            results.append(make_result(
                DOMAIN, "Pressure Tendency Code", tendency_str,
                "0–8 or /", tendency_str, ValidationStatus.WARNING,
                "Pressure tendency code is missing (/).",
                "Determine the 3-hour pressure tendency."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Pressure Tendency Code", tendency_str,
                "0–8", tendency_str, ValidationStatus.ERROR,
                f"Pressure tendency code '{tendency_str}' is invalid.",
                "Use WMO Code Table 0200 (values 0–8)."
            ))

    # ------------------------------------------------------------------
    # 5. Pressure change — consistency with tendency code
    # ------------------------------------------------------------------
    if change is not None and tendency is not None:
        tendency_str = str(tendency)
        abs_change = abs(change)

        # Check sign consistency
        if tendency_str in A_RISING and change < -0.1:
            results.append(make_result(
                DOMAIN, "Tendency/Change Consistency",
                f"a={tendency_str}, ppp={change}",
                "Rising tendency (a=0–3) should have positive or zero change",
                f"Change = {change} hPa",
                ValidationStatus.WARNING,
                f"Tendency code '{tendency_str}' indicates rising pressure, "
                f"but the 3h change is {change} hPa (negative).",
                "Verify the tendency code and 3-hour pressure change."
            ))
        elif tendency_str in A_FALLING and change > 0.1:
            results.append(make_result(
                DOMAIN, "Tendency/Change Consistency",
                f"a={tendency_str}, ppp={change}",
                "Falling tendency (a=5–8) should have negative or zero change",
                f"Change = {change} hPa",
                ValidationStatus.WARNING,
                f"Tendency code '{tendency_str}' indicates falling pressure, "
                f"but the 3h change is +{change} hPa (positive).",
                "Verify the tendency code and 3-hour pressure change."
            ))
        elif tendency_str in A_STEADY and abs_change > 0.5:
            results.append(make_result(
                DOMAIN, "Tendency/Change Consistency",
                f"a={tendency_str}, ppp={change}",
                "Steady tendency (a=4) should have near-zero change",
                f"Change = {change} hPa",
                ValidationStatus.WARNING,
                f"Tendency code '4' (steady) but 3h change is {change} hPa.",
                "Verify: is the pressure truly steady?"
            ))
        else:
            results.append(make_result(
                DOMAIN, "Tendency/Change Consistency",
                f"a={tendency_str}, ppp={change}",
                "Tendency code matches sign of pressure change",
                f"Consistent",
                ValidationStatus.PASS,
                "Pressure tendency code is consistent with the 3h change."
            ))

    # ------------------------------------------------------------------
    # 6. Abnormal pressure change detection
    # ------------------------------------------------------------------
    if change is not None:
        abs_change = abs(change)
        if abs_change <= 10.0:
            results.append(make_result(
                DOMAIN, "Pressure Change Magnitude", change,
                "3h change ≤ 10 hPa (normal)", f"{change} hPa",
                ValidationStatus.PASS,
                f"3-hour pressure change ({change} hPa) is within normal limits."
            ))
        elif abs_change <= 15.0:
            results.append(make_result(
                DOMAIN, "Pressure Change Magnitude", change,
                "3h change ≤ 10 hPa (normal)", f"{change} hPa",
                ValidationStatus.WARNING,
                f"3-hour pressure change ({change} hPa) is unusually large. "
                "This may indicate an intense weather system.",
                "Verify the barometer reading against neighboring stations."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Pressure Change Magnitude", change,
                "3h change ≤ 10 hPa (normal)", f"{change} hPa",
                ValidationStatus.ERROR,
                f"3-hour pressure change ({change} hPa) is extremely large "
                "and likely erroneous.",
                "Re-read the barometer. Compare with nearby station data."
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
