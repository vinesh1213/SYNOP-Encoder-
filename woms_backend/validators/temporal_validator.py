# =============================================================================
# SYNOP Validation Engine — Temporal Consistency Validator
# =============================================================================
# Requirement §11: Compares current observation with previous observations.
#   - Temperature change: |ΔT| > 10 °C/3h → WARNING
#   - Pressure change: |ΔP| > 10 hPa/3h → WARNING
#   - Wind speed change: |Δff| > 40 kt/3h → WARNING
#   - Humidity change: |ΔRH| > 50%/3h → WARNING
#   - Rainfall trend: non-decreasing accumulation
#
# The previous observation is passed as an optional dict by the caller.
# This keeps validators pure (no DB access).
# =============================================================================

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result

logger = logging.getLogger(__name__)

DOMAIN = "temporal"

# Thresholds for flagging sudden changes (per 3-hour period)
TEMP_CHANGE_WARNING = 10.0    # °C
TEMP_CHANGE_ERROR = 20.0      # °C
PRESSURE_CHANGE_WARNING = 10.0  # hPa
PRESSURE_CHANGE_ERROR = 20.0    # hPa
WIND_CHANGE_WARNING = 40.0    # knots (or equivalent)
WIND_CHANGE_ERROR = 80.0      # knots
RH_CHANGE_WARNING = 50.0      # %
RH_CHANGE_ERROR = 80.0        # %


def validate_temporal(
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]] = None,
) -> List[ValidationResult]:
    """
    Validate temporal consistency between the current and previous observation.

    Parameters
    ----------
    current : dict
        Current observation data dictionary.
    previous : dict or None
        Previous observation data (same station, earlier time).
        If None, temporal checks are skipped.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    if previous is None:
        results.append(make_result(
            DOMAIN, "Previous Observation", None,
            "Previous observation for comparison",
            "(not available)",
            ValidationStatus.PASS,
            "No previous observation available — temporal checks skipped."
        ))
        return results

    # ------------------------------------------------------------------
    # 1. Temperature change
    # ------------------------------------------------------------------
    curr_t = _to_float(current.get("dry_bulb"))
    prev_t = _to_float(previous.get("dry_bulb"))
    if curr_t is not None and prev_t is not None:
        delta = abs(curr_t - prev_t)
        results.append(_check_change(
            "Temperature", curr_t, prev_t, "°C",
            TEMP_CHANGE_WARNING, TEMP_CHANGE_ERROR
        ))

    # ------------------------------------------------------------------
    # 2. Pressure change
    # ------------------------------------------------------------------
    curr_p = _to_float(current.get("station_pressure"))
    prev_p = _to_float(previous.get("station_pressure"))
    if curr_p is not None and prev_p is not None:
        results.append(_check_change(
            "Station Pressure", curr_p, prev_p, "hPa",
            PRESSURE_CHANGE_WARNING, PRESSURE_CHANGE_ERROR
        ))

    # MSL pressure
    curr_msl = _to_float(current.get("msl_pressure"))
    prev_msl = _to_float(previous.get("msl_pressure"))
    if curr_msl is not None and prev_msl is not None:
        results.append(_check_change(
            "MSL Pressure", curr_msl, prev_msl, "hPa",
            PRESSURE_CHANGE_WARNING, PRESSURE_CHANGE_ERROR
        ))

    # ------------------------------------------------------------------
    # 3. Wind speed change
    # ------------------------------------------------------------------
    curr_ws = _to_float(current.get("wind_speed"))
    prev_ws = _to_float(previous.get("wind_speed"))
    if curr_ws is not None and prev_ws is not None:
        results.append(_check_change(
            "Wind Speed", curr_ws, prev_ws,
            current.get("wind_unit", "units"),
            WIND_CHANGE_WARNING, WIND_CHANGE_ERROR
        ))

    # ------------------------------------------------------------------
    # 4. Humidity change (computed from dew point and temperature)
    # ------------------------------------------------------------------
    curr_rh = _compute_rh(current)
    prev_rh = _compute_rh(previous)
    if curr_rh is not None and prev_rh is not None:
        results.append(_check_change(
            "Relative Humidity", curr_rh, prev_rh, "%",
            RH_CHANGE_WARNING, RH_CHANGE_ERROR
        ))

    # ------------------------------------------------------------------
    # 5. Rainfall trend — should not decrease within accumulation period
    # ------------------------------------------------------------------
    curr_rain = _to_float(current.get("rainfall"))
    prev_rain = _to_float(previous.get("rainfall"))
    if curr_rain is not None and prev_rain is not None:
        if curr_rain < prev_rain:
            results.append(make_result(
                DOMAIN, "Rainfall Trend",
                f"Current={curr_rain}, Previous={prev_rain}",
                "Accumulated rainfall should not decrease",
                f"{curr_rain} < {prev_rain}",
                ValidationStatus.WARNING,
                f"Rainfall ({curr_rain} mm) is less than the previous "
                f"observation ({prev_rain} mm). Accumulated rainfall "
                "should not decrease unless a new accumulation period started.",
                "Verify if the rain gauge was reset or if this is a new period."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Rainfall Trend",
                f"Current={curr_rain}, Previous={prev_rain}",
                "Accumulated rainfall non-decreasing",
                f"{curr_rain} ≥ {prev_rain}",
                ValidationStatus.PASS,
                "Rainfall trend is consistent."
            ))

    # ------------------------------------------------------------------
    # 6. Wind direction sudden reversal
    # ------------------------------------------------------------------
    curr_wd = _to_float(current.get("wind_direction"))
    prev_wd = _to_float(previous.get("wind_direction"))
    if curr_wd is not None and prev_wd is not None:
        if curr_wd > 0 and prev_wd > 0:  # exclude calm
            angle_diff = abs(curr_wd - prev_wd)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            if angle_diff > 150:
                results.append(make_result(
                    DOMAIN, "Wind Direction Reversal",
                    f"Current={curr_wd}°, Previous={prev_wd}°",
                    "Direction change ≤ 150° between observations",
                    f"Δ = {angle_diff}°",
                    ValidationStatus.WARNING,
                    f"Wind direction changed by {angle_diff}° since the "
                    "previous observation. This may indicate a frontal passage.",
                    "Verify wind instrument and note any frontal activity."
                ))

    return results


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _check_change(
    name: str,
    current_val: float,
    previous_val: float,
    unit: str,
    warn_threshold: float,
    error_threshold: float,
) -> ValidationResult:
    """Check the magnitude of change between consecutive observations."""
    delta = abs(current_val - previous_val)
    direction = "increased" if current_val > previous_val else "decreased"

    if delta <= warn_threshold:
        return make_result(
            DOMAIN, f"{name} Change",
            f"Current={current_val}, Previous={previous_val}",
            f"|Δ| ≤ {warn_threshold} {unit}",
            f"Δ = {delta:.1f} {unit}",
            ValidationStatus.PASS,
            f"{name} {direction} by {delta:.1f} {unit} — within normal limits."
        )
    elif delta <= error_threshold:
        return make_result(
            DOMAIN, f"{name} Change",
            f"Current={current_val}, Previous={previous_val}",
            f"|Δ| ≤ {warn_threshold} {unit}",
            f"Δ = {delta:.1f} {unit}",
            ValidationStatus.WARNING,
            f"{name} {direction} by {delta:.1f} {unit} since the previous "
            "observation. This is an unusually large change.",
            f"Verify the {name.lower()} reading."
        )
    else:
        return make_result(
            DOMAIN, f"{name} Change",
            f"Current={current_val}, Previous={previous_val}",
            f"|Δ| ≤ {warn_threshold} {unit}",
            f"Δ = {delta:.1f} {unit}",
            ValidationStatus.ERROR,
            f"{name} {direction} by {delta:.1f} {unit} since the previous "
            "observation. This is an extremely large and likely erroneous change.",
            f"Re-read the instrument. Compare with nearby stations."
        )


def _compute_rh(data: Dict[str, Any]) -> Optional[float]:
    """Compute RH from dry bulb and dew point using Magnus formula."""
    t = _to_float(data.get("dry_bulb"))
    td = _to_float(data.get("dew_point"))
    if t is None or td is None:
        return None
    try:
        a, b = 17.27, 237.7
        e = math.exp((a * td) / (b + td))
        es = math.exp((a * t) / (b + t))
        return round((e / es) * 100.0, 1)
    except Exception:
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
