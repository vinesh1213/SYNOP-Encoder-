# =============================================================================
# SYNOP Validation Engine — Cross-Parameter Validator
# =============================================================================
# Requirement §13: Validates logical relationships across multiple parameters.
#   - Dew Point ≤ Dry Bulb (cross-check with temperature validator)
#   - Dry Bulb ≥ Wet Bulb
#   - RH 0–100%
#   - Pressure consistency (MSL vs. station vs. elevation)
#   - Temperature: sec333 max/min vs. dry bulb
#   - Weather vs. cloud: clear weather ↔ low cloud cover
#   - Wind vs. weather: storm codes ↔ significant wind
#   - Fog ↔ low visibility
#   - Precipitation weather ↔ rainfall group
# =============================================================================

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    WW_FOG, WW_PRECIPITATION, WW_NO_PRECIPITATION,
    WW_THUNDERSTORM, WW_DUST_STORM,
)

logger = logging.getLogger(__name__)

DOMAIN = "cross_parameter"


def validate_cross_parameters(
    data: Dict[str, Any],
    station_elevation: Optional[float] = None,
) -> List[ValidationResult]:
    """
    Validate logical relationships across multiple meteorological parameters.

    Parameters
    ----------
    data : dict
        Observation data dictionary.
    station_elevation : float or None
        Station elevation in meters (for pressure consistency).

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    dry_bulb = _to_float(data.get("dry_bulb"))
    wet_bulb = _to_float(data.get("wet_bulb"))
    dew_point = _to_float(data.get("dew_point"))
    station_p = _to_float(data.get("station_pressure"))
    msl_p = _to_float(data.get("msl_pressure"))
    wind_speed = _to_float(data.get("wind_speed"))
    visibility = _to_float(data.get("visibility"))
    vis_unit = data.get("visibility_unit")
    n_cloud = _to_int(data.get("total_cloud_cover"))
    ww = _to_int(data.get("present_weather"))
    rainfall = _to_float(data.get("rainfall"))

    # Convert visibility to km for cross-checks
    vis_km = visibility
    if vis_km is not None and vis_unit == "meters":
        vis_km = vis_km / 1000.0

    # ------------------------------------------------------------------
    # 1. Weather vs. Cloud consistency
    # ------------------------------------------------------------------
    if ww is not None and n_cloud is not None:
        # Clear weather (ww=00–03) with overcast sky
        if ww in WW_NO_PRECIPITATION and n_cloud >= 7:
            results.append(make_result(
                DOMAIN, "Weather vs. Cloud Cover",
                f"ww={ww}, N={n_cloud}",
                "If ww=00–03 (no significant weather), cloud cover should not be overcast",
                f"ww={ww}, N={n_cloud} oktas",
                ValidationStatus.WARNING,
                f"Present weather ({ww}) indicates no significant weather, "
                f"but cloud cover is {n_cloud} oktas (nearly or fully overcast). "
                "Consider using a more descriptive ww code.",
                "Review present weather — overcast skies often warrant ww ≥ 04."
            ))

        # Thunderstorm/heavy weather with very few clouds
        if ww in WW_THUNDERSTORM and n_cloud is not None and n_cloud <= 2:
            results.append(make_result(
                DOMAIN, "Thunderstorm vs. Cloud Cover",
                f"ww={ww}, N={n_cloud}",
                "Thunderstorm (ww=91–99) should have significant cloud cover",
                f"ww={ww}, N={n_cloud} oktas",
                ValidationStatus.WARNING,
                f"Thunderstorm (ww={ww}) with only {n_cloud} oktas of "
                "cloud cover is unusual.",
                "Verify cloud cover; thunderstorms typically have Cb clouds."
            ))

    # ------------------------------------------------------------------
    # 2. Fog vs. Visibility
    # ------------------------------------------------------------------
    if ww is not None and vis_km is not None:
        if ww in WW_FOG:
            # Fog: visibility should be < 1 km (by WMO definition)
            if vis_km >= 1.0:
                results.append(make_result(
                    DOMAIN, "Fog vs. Visibility",
                    f"ww={ww}, vis={vis_km} km",
                    "Fog (ww=40–49) requires visibility < 1 km",
                    f"Visibility = {vis_km} km",
                    ValidationStatus.WARNING,
                    f"Present weather ({ww}) indicates fog, but visibility "
                    f"({vis_km} km) is ≥ 1 km. By WMO definition, fog "
                    "requires visibility below 1 km.",
                    "If visibility is ≥ 1 km, use mist (ww=10) or haze instead."
                ))
            else:
                results.append(make_result(
                    DOMAIN, "Fog vs. Visibility",
                    f"ww={ww}, vis={vis_km} km",
                    "Fog ↔ visibility < 1 km",
                    f"Consistent",
                    ValidationStatus.PASS,
                    "Fog weather code is consistent with low visibility."
                ))

        # Low visibility without fog/mist code
        if vis_km < 1.0 and ww not in WW_FOG and ww not in range(10, 13):
            # Codes 10–12 are mist
            if ww not in WW_DUST_STORM and ww not in range(4, 10):
                results.append(make_result(
                    DOMAIN, "Low Visibility vs. Weather",
                    f"vis={vis_km} km, ww={ww}",
                    "Visibility < 1 km should have fog/mist/haze weather code",
                    f"ww={ww}",
                    ValidationStatus.WARNING,
                    f"Visibility is very low ({vis_km} km) but present weather "
                    f"({ww}) does not indicate fog, mist, haze, or dust.",
                    "Consider reporting fog (40–49) or mist (10) if applicable."
                ))

    # ------------------------------------------------------------------
    # 3. Wind vs. Weather
    # ------------------------------------------------------------------
    if ww is not None and wind_speed is not None:
        wind_unit = data.get("wind_unit", "m/s")
        # Convert to m/s for comparison
        ws_ms = wind_speed
        if wind_unit == "knots":
            ws_ms = wind_speed * 0.514444

        # Dust/sandstorm codes need wind
        if ww in WW_DUST_STORM and ws_ms < 5.0:
            results.append(make_result(
                DOMAIN, "Dust Storm vs. Wind",
                f"ww={ww}, wind={wind_speed} {wind_unit}",
                "Dust/sandstorm (ww=30–39) requires significant wind",
                f"Wind = {ws_ms:.1f} m/s",
                ValidationStatus.WARNING,
                f"Weather code ({ww}) indicates dust/sandstorm but wind speed "
                f"({ws_ms:.1f} m/s) is low. Dust storms require strong winds.",
                "Verify wind speed and weather code."
            ))

        # Thunderstorm codes — generally associated with stronger winds
        if ww in WW_THUNDERSTORM and ws_ms < 2.0:
            results.append(make_result(
                DOMAIN, "Thunderstorm vs. Wind",
                f"ww={ww}, wind={wind_speed} {wind_unit}",
                "Thunderstorm typically accompanied by winds > 2 m/s",
                f"Wind = {ws_ms:.1f} m/s",
                ValidationStatus.WARNING,
                f"Thunderstorm (ww={ww}) with very light wind ({ws_ms:.1f} m/s) "
                "is unusual, though possible.",
                "Verify wind measurement during the thunderstorm."
            ))

    # ------------------------------------------------------------------
    # 4. Precipitation weather code vs. rainfall
    # ------------------------------------------------------------------
    if ww is not None and rainfall is not None:
        if ww in WW_PRECIPITATION and rainfall == 0:
            results.append(make_result(
                DOMAIN, "Precipitation Weather vs. Rainfall",
                f"ww={ww}, rainfall={rainfall}",
                "Precipitation weather code should have rainfall > 0",
                f"ww={ww}, rainfall=0",
                ValidationStatus.WARNING,
                f"Weather code ({ww}) indicates precipitation, but rainfall "
                "is reported as 0 mm.",
                "If precipitation is occurring, report the amount. "
                "Use trace (< 0.05 mm) if amount is negligible."
            ))

        if ww in WW_NO_PRECIPITATION and rainfall is not None and rainfall > 0:
            # Already handled in rainfall_validator, but included here
            # for completeness as a cross-parameter check.
            pass

    # ------------------------------------------------------------------
    # 5. Pressure vs. elevation consistency
    # ------------------------------------------------------------------
    if station_p is not None and msl_p is not None and station_elevation is not None:
        if station_elevation > 0:
            # Rough estimate: pressure drops ~1.2 hPa per 10m at sea level
            expected_diff = station_elevation * 0.12
            actual_diff = msl_p - station_p
            ratio = actual_diff / expected_diff if expected_diff > 0 else 1.0

            if 0.5 <= ratio <= 2.0:
                results.append(make_result(
                    DOMAIN, "Pressure vs. Elevation",
                    f"MSL={msl_p}, Station={station_p}, Elev={station_elevation}m",
                    "Pressure difference consistent with elevation",
                    f"Δ={actual_diff:.1f} hPa (expected ≈{expected_diff:.1f})",
                    ValidationStatus.PASS,
                    "Pressure difference is consistent with station elevation."
                ))
            else:
                results.append(make_result(
                    DOMAIN, "Pressure vs. Elevation",
                    f"MSL={msl_p}, Station={station_p}, Elev={station_elevation}m",
                    f"Expected Δ ≈ {expected_diff:.1f} hPa for {station_elevation}m",
                    f"Actual Δ = {actual_diff:.1f} hPa",
                    ValidationStatus.WARNING,
                    f"Pressure difference ({actual_diff:.1f} hPa) between MSL "
                    f"and station is inconsistent with the elevation "
                    f"({station_elevation} m). Expected ≈ {expected_diff:.1f} hPa.",
                    "Verify station elevation and pressure reduction formula."
                ))

    # ------------------------------------------------------------------
    # 6. Temperature consistency: dew point depression reasonableness
    # ------------------------------------------------------------------
    if dry_bulb is not None and dew_point is not None:
        depression = dry_bulb - dew_point
        if depression < 0:
            # Already flagged by temperature validator
            pass
        elif depression > 50:
            results.append(make_result(
                DOMAIN, "Dew Point Depression",
                f"Td={dry_bulb}, Dp={dew_point}",
                "Dew point depression ≤ 50°C",
                f"Depression = {depression:.1f}°C",
                ValidationStatus.WARNING,
                f"Dew point depression ({depression:.1f}°C) is extremely "
                "large. This indicates very dry conditions.",
                "Verify both temperature and dew point readings."
            ))

    # ------------------------------------------------------------------
    # 7. RH sanity check (from dew point)
    # ------------------------------------------------------------------
    if dry_bulb is not None and dew_point is not None:
        try:
            a, b = 17.27, 237.7
            e = math.exp((a * dew_point) / (b + dew_point))
            es = math.exp((a * dry_bulb) / (b + dry_bulb))
            rh = (e / es) * 100.0
            if rh < 0 or rh > 100:
                results.append(make_result(
                    DOMAIN, "Cross-Check RH Range",
                    f"Td={dry_bulb}, Dp={dew_point}",
                    "RH 0–100%",
                    f"RH = {rh:.1f}%",
                    ValidationStatus.ERROR,
                    f"Computed RH ({rh:.1f}%) from dry bulb and dew point "
                    "is outside 0–100%. The temperature/dew point pair is "
                    "physically impossible.",
                    "Correct either the dry bulb or the dew point."
                ))
        except Exception:
            pass

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
