# =============================================================================
# SYNOP Validation Engine — Humidity Validator
# =============================================================================
# Requirement §4: Validates humidity-related observations.
#   - Calculates RH from dry bulb, wet bulb, and pressure
#   - RH must be between 0% and 100%
#   - Dew point consistency
#   - Psychrometric relationships
# =============================================================================

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result

logger = logging.getLogger(__name__)

DOMAIN = "humidity"


def validate_humidity(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate humidity observations and psychrometric consistency.

    Parameters
    ----------
    data : dict
        Observation data with keys: dry_bulb, wet_bulb, dew_point,
        station_pressure.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    dry_bulb = _to_float(data.get("dry_bulb"))
    wet_bulb = _to_float(data.get("wet_bulb"))
    dew_point = _to_float(data.get("dew_point"))
    pressure = _to_float(data.get("station_pressure"))

    # Need at least dry bulb for any humidity check
    if dry_bulb is None:
        return results

    # ------------------------------------------------------------------
    # 1. Calculate RH from dry bulb and dew point (if available)
    # ------------------------------------------------------------------
    rh_from_dew = None
    if dew_point is not None:
        rh_from_dew = _calculate_rh_from_dewpoint(dry_bulb, dew_point)

        if rh_from_dew is not None:
            if 0.0 <= rh_from_dew <= 100.0:
                results.append(make_result(
                    DOMAIN, "RH from Dew Point", f"Td={dry_bulb}, Dp={dew_point}",
                    "0% – 100%", f"{rh_from_dew:.1f}%",
                    ValidationStatus.PASS,
                    f"Relative humidity calculated from dew point: {rh_from_dew:.1f}%."
                ))
            else:
                results.append(make_result(
                    DOMAIN, "RH from Dew Point", f"Td={dry_bulb}, Dp={dew_point}",
                    "0% – 100%", f"{rh_from_dew:.1f}%",
                    ValidationStatus.ERROR,
                    f"RH from dew point ({rh_from_dew:.1f}%) is outside 0–100%. "
                    "This indicates inconsistent temperature/dew point values.",
                    "Re-check the dew point temperature."
                ))

    # ------------------------------------------------------------------
    # 2. Calculate RH from psychrometric formula (dry/wet bulb + pressure)
    # ------------------------------------------------------------------
    rh_from_psychro = None
    if wet_bulb is not None and pressure is not None:
        rh_from_psychro = _calculate_rh_psychrometric(
            dry_bulb, wet_bulb, pressure
        )

        if rh_from_psychro is not None:
            if 0.0 <= rh_from_psychro <= 100.0:
                results.append(make_result(
                    DOMAIN, "RH from Psychrometer",
                    f"Td={dry_bulb}, Tw={wet_bulb}, P={pressure}",
                    "0% – 100%", f"{rh_from_psychro:.1f}%",
                    ValidationStatus.PASS,
                    f"Relative humidity from psychrometric formula: "
                    f"{rh_from_psychro:.1f}%."
                ))
            else:
                # Values slightly outside (e.g. 101% due to rounding) → WARNING
                severity = (
                    ValidationStatus.WARNING
                    if -5.0 <= rh_from_psychro <= 105.0
                    else ValidationStatus.ERROR
                )
                results.append(make_result(
                    DOMAIN, "RH from Psychrometer",
                    f"Td={dry_bulb}, Tw={wet_bulb}, P={pressure}",
                    "0% – 100%", f"{rh_from_psychro:.1f}%",
                    severity,
                    f"RH from psychrometric formula ({rh_from_psychro:.1f}%) "
                    "is outside the valid range.",
                    "Check the wet bulb and dry bulb readings."
                ))

    # ------------------------------------------------------------------
    # 3. Cross-check: RH from dew point vs. RH from psychrometer
    # ------------------------------------------------------------------
    if rh_from_dew is not None and rh_from_psychro is not None:
        rh_diff = abs(rh_from_dew - rh_from_psychro)
        if rh_diff <= 5.0:
            results.append(make_result(
                DOMAIN, "RH Cross-Consistency",
                f"RH(dp)={rh_from_dew:.1f}%, RH(psy)={rh_from_psychro:.1f}%",
                "Difference ≤ 5%",
                f"Δ = {rh_diff:.1f}%",
                ValidationStatus.PASS,
                f"RH methods agree within {rh_diff:.1f}%."
            ))
        elif rh_diff <= 15.0:
            results.append(make_result(
                DOMAIN, "RH Cross-Consistency",
                f"RH(dp)={rh_from_dew:.1f}%, RH(psy)={rh_from_psychro:.1f}%",
                "Difference ≤ 5%",
                f"Δ = {rh_diff:.1f}%",
                ValidationStatus.WARNING,
                f"RH from dew point ({rh_from_dew:.1f}%) differs from "
                f"psychrometric RH ({rh_from_psychro:.1f}%) by {rh_diff:.1f}%.",
                "Verify thermometer readings and dew point calculation."
            ))
        else:
            results.append(make_result(
                DOMAIN, "RH Cross-Consistency",
                f"RH(dp)={rh_from_dew:.1f}%, RH(psy)={rh_from_psychro:.1f}%",
                "Difference ≤ 5%",
                f"Δ = {rh_diff:.1f}%",
                ValidationStatus.ERROR,
                f"RH values are significantly inconsistent: dew point method "
                f"gives {rh_from_dew:.1f}% while psychrometric method gives "
                f"{rh_from_psychro:.1f}% (Δ = {rh_diff:.1f}%).",
                "Re-read all thermometers and recalculate."
            ))

    # ------------------------------------------------------------------
    # 4. Dew point consistency: recalculate dew point from RH
    # ------------------------------------------------------------------
    if dew_point is not None and rh_from_psychro is not None:
        computed_dp = _calculate_dewpoint(dry_bulb, rh_from_psychro)
        if computed_dp is not None:
            dp_diff = abs(dew_point - computed_dp)
            if dp_diff <= 2.0:
                results.append(make_result(
                    DOMAIN, "Dew Point Consistency",
                    f"Reported={dew_point}°C, Computed={computed_dp:.1f}°C",
                    "Difference ≤ 2°C",
                    f"Δ = {dp_diff:.1f}°C",
                    ValidationStatus.PASS,
                    f"Reported dew point is consistent with psychrometric "
                    f"computation (Δ = {dp_diff:.1f}°C)."
                ))
            elif dp_diff <= 5.0:
                results.append(make_result(
                    DOMAIN, "Dew Point Consistency",
                    f"Reported={dew_point}°C, Computed={computed_dp:.1f}°C",
                    "Difference ≤ 2°C",
                    f"Δ = {dp_diff:.1f}°C",
                    ValidationStatus.WARNING,
                    f"Reported dew point ({dew_point}°C) differs from computed "
                    f"dew point ({computed_dp:.1f}°C) by {dp_diff:.1f}°C.",
                    "Verify dew point derivation from psychrometric tables."
                ))
            else:
                results.append(make_result(
                    DOMAIN, "Dew Point Consistency",
                    f"Reported={dew_point}°C, Computed={computed_dp:.1f}°C",
                    "Difference ≤ 2°C",
                    f"Δ = {dp_diff:.1f}°C",
                    ValidationStatus.ERROR,
                    f"Reported dew point ({dew_point}°C) is significantly "
                    f"different from computed value ({computed_dp:.1f}°C).",
                    "Recalculate dew point from wet/dry bulb readings."
                ))

    # ------------------------------------------------------------------
    # 5. Wet bulb depression reasonableness
    # ------------------------------------------------------------------
    if dry_bulb is not None and wet_bulb is not None:
        depression = round(dry_bulb - wet_bulb, 1)
        if depression < 0:
            # Already caught by temperature validator, but flag here too
            pass
        elif depression > 30.0:
            results.append(make_result(
                DOMAIN, "Wet Bulb Depression",
                f"Td={dry_bulb}, Tw={wet_bulb}",
                "Wet bulb depression ≤ 30°C",
                f"{depression}°C",
                ValidationStatus.WARNING,
                f"Wet bulb depression ({depression}°C) is unusually large.",
                "Check if the wet bulb wick is dry or detached."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Wet Bulb Depression",
                f"Td={dry_bulb}, Tw={wet_bulb}",
                "Wet bulb depression ≤ 30°C",
                f"{depression}°C",
                ValidationStatus.PASS,
                f"Wet bulb depression ({depression}°C) is within normal range."
            ))

    return results


# -----------------------------------------------------------------------
# Psychrometric calculations
# -----------------------------------------------------------------------

def _saturation_vapor_pressure(t: float) -> float:
    """
    Calculate saturation vapor pressure (hPa) using the Magnus-Tetens formula.

    Parameters
    ----------
    t : float
        Temperature in °C.

    Returns
    -------
    float
        Saturation vapor pressure in hPa.
    """
    a = 17.27
    b = 237.7
    return 6.1078 * math.exp((a * t) / (b + t))


def _calculate_rh_from_dewpoint(t: float, td: float) -> Optional[float]:
    """Calculate RH (%) from air temperature and dew point."""
    try:
        es = _saturation_vapor_pressure(t)
        e = _saturation_vapor_pressure(td)
        rh = (e / es) * 100.0
        return round(rh, 1)
    except Exception:
        return None


def _calculate_rh_psychrometric(
    t_dry: float, t_wet: float, pressure: float
) -> Optional[float]:
    """
    Calculate RH (%) using the Sprung psychrometric formula.

    RH = 100 * [e_wet - A * P * (T_dry - T_wet)] / e_dry

    where A ≈ 0.000799 (psychrometer coefficient for Assmann aspirated).
    """
    try:
        A = 0.000799  # Assmann ventilated psychrometer coefficient
        e_sat_dry = _saturation_vapor_pressure(t_dry)
        e_sat_wet = _saturation_vapor_pressure(t_wet)

        e_actual = e_sat_wet - A * pressure * (t_dry - t_wet)
        rh = (e_actual / e_sat_dry) * 100.0
        return round(rh, 1)
    except Exception:
        return None


def _calculate_dewpoint(t: float, rh: float) -> Optional[float]:
    """Calculate dew point (°C) from temperature and RH using Magnus formula."""
    try:
        if rh <= 0:
            return None
        a = 17.27
        b = 237.7
        alpha = ((a * t) / (b + t)) + math.log(rh / 100.0)
        td = (b * alpha) / (a - alpha)
        return round(td, 1)
    except Exception:
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
