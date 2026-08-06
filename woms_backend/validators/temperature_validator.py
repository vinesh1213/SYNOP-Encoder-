# =============================================================================
# SYNOP Validation Engine — Temperature Validator
# =============================================================================
# Requirement §3: Validates all temperature-related observations.
#   - Air temperature range (−80 °C to +60 °C)
#   - Dry Bulb ≥ Wet Bulb
#   - Dew Point ≤ Air Temperature
#   - Max Temperature ≥ Current Temperature
#   - Min Temperature ≤ Current Temperature
#   - Decimal precision
#   - Impossible value detection
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import TEMPERATURE_MIN, TEMPERATURE_MAX

logger = logging.getLogger(__name__)

DOMAIN = "temperature"


def validate_temperature(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate all temperature fields from an observation data dictionary.

    Expected keys: dry_bulb, wet_bulb, dew_point, max_temperature,
    min_temperature, sec333_max_temperature, sec333_min_temperature.

    Parameters
    ----------
    data : dict
        Observation data dictionary (field names match ObservationSchema).

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    dry_bulb = _to_float(data.get("dry_bulb"))
    wet_bulb = _to_float(data.get("wet_bulb"))
    dew_point = _to_float(data.get("dew_point"))
    max_temp = _to_float(data.get("max_temperature"))
    min_temp = _to_float(data.get("min_temperature"))
    sec333_max = _to_float(data.get("sec333_max_temperature"))
    sec333_min = _to_float(data.get("sec333_min_temperature"))

    # ------------------------------------------------------------------
    # 1. Dry Bulb — range check
    # ------------------------------------------------------------------
    if dry_bulb is not None:
        results.append(_range_check(
            "Dry Bulb Temperature", dry_bulb, TEMPERATURE_MIN, TEMPERATURE_MAX
        ))

        # Decimal precision — WMO expects tenths of a degree
        results.append(_precision_check("Dry Bulb", data.get("dry_bulb")))
    else:
        results.append(make_result(
            DOMAIN, "Dry Bulb Presence", None,
            "Dry bulb temperature is mandatory",
            None, ValidationStatus.ERROR,
            "Dry bulb temperature is missing. This field is mandatory for SYNOP encoding.",
            "Enter the dry bulb temperature in °C."
        ))

    # ------------------------------------------------------------------
    # 2. Wet Bulb — range check
    # ------------------------------------------------------------------
    if wet_bulb is not None:
        results.append(_range_check(
            "Wet Bulb Temperature", wet_bulb, TEMPERATURE_MIN, TEMPERATURE_MAX
        ))
        results.append(_precision_check("Wet Bulb", data.get("wet_bulb")))

    # ------------------------------------------------------------------
    # 3. Dew Point — range check
    # ------------------------------------------------------------------
    if dew_point is not None:
        results.append(_range_check(
            "Dew Point Temperature", dew_point, TEMPERATURE_MIN, TEMPERATURE_MAX
        ))
        results.append(_precision_check("Dew Point", data.get("dew_point")))

    # ------------------------------------------------------------------
    # 4. Dry Bulb ≥ Wet Bulb
    # ------------------------------------------------------------------
    if dry_bulb is not None and wet_bulb is not None:
        if dry_bulb >= wet_bulb:
            results.append(make_result(
                DOMAIN, "Dry Bulb ≥ Wet Bulb", f"Td={dry_bulb}, Tw={wet_bulb}",
                "Dry bulb ≥ Wet bulb",
                f"{dry_bulb} ≥ {wet_bulb}", ValidationStatus.PASS,
                "Dry bulb temperature is correctly ≥ wet bulb temperature."
            ))
        else:
            diff = round(wet_bulb - dry_bulb, 1)
            results.append(make_result(
                DOMAIN, "Dry Bulb ≥ Wet Bulb", f"Td={dry_bulb}, Tw={wet_bulb}",
                "Dry bulb ≥ Wet bulb",
                f"{dry_bulb} < {wet_bulb} (diff={diff}°C)",
                ValidationStatus.ERROR,
                f"Wet bulb ({wet_bulb}°C) exceeds dry bulb ({dry_bulb}°C) by {diff}°C. "
                "This violates the psychrometric relationship.",
                "Re-read the wet and dry bulb thermometers."
            ))

    # ------------------------------------------------------------------
    # 5. Dew Point ≤ Dry Bulb
    # ------------------------------------------------------------------
    if dry_bulb is not None and dew_point is not None:
        if dew_point <= dry_bulb:
            results.append(make_result(
                DOMAIN, "Dew Point ≤ Dry Bulb", f"Dp={dew_point}, Td={dry_bulb}",
                "Dew point ≤ Dry bulb",
                f"{dew_point} ≤ {dry_bulb}", ValidationStatus.PASS,
                "Dew point is correctly ≤ dry bulb temperature."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Dew Point ≤ Dry Bulb", f"Dp={dew_point}, Td={dry_bulb}",
                "Dew point ≤ Dry bulb",
                f"{dew_point} > {dry_bulb}",
                ValidationStatus.ERROR,
                f"Dew point ({dew_point}°C) exceeds dry bulb ({dry_bulb}°C). "
                "Dew point can never exceed the air temperature.",
                "Verify the dew point calculation and dry bulb reading."
            ))

    # ------------------------------------------------------------------
    # 6. Dew Point ≤ Wet Bulb (additional cross-check)
    # ------------------------------------------------------------------
    if wet_bulb is not None and dew_point is not None:
        if dew_point <= wet_bulb:
            results.append(make_result(
                DOMAIN, "Dew Point ≤ Wet Bulb", f"Dp={dew_point}, Tw={wet_bulb}",
                "Dew point ≤ Wet bulb",
                f"{dew_point} ≤ {wet_bulb}", ValidationStatus.PASS,
                "Dew point is correctly ≤ wet bulb temperature."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Dew Point ≤ Wet Bulb", f"Dp={dew_point}, Tw={wet_bulb}",
                "Dew point ≤ Wet bulb",
                f"{dew_point} > {wet_bulb}",
                ValidationStatus.ERROR,
                f"Dew point ({dew_point}°C) exceeds wet bulb ({wet_bulb}°C).",
                "Verify the dew point and wet bulb readings."
            ))

    # ------------------------------------------------------------------
    # 7. Max Temperature ≥ Current Temperature
    # ------------------------------------------------------------------
    current_temp = dry_bulb
    max_t = sec333_max if sec333_max is not None else max_temp

    if current_temp is not None and max_t is not None:
        if max_t >= current_temp:
            results.append(make_result(
                DOMAIN, "Max Temp ≥ Current Temp",
                f"Tmax={max_t}, Tcurr={current_temp}",
                "Maximum temperature ≥ current temperature",
                f"{max_t} ≥ {current_temp}", ValidationStatus.PASS,
                "Maximum temperature is correctly ≥ current temperature."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Max Temp ≥ Current Temp",
                f"Tmax={max_t}, Tcurr={current_temp}",
                "Maximum temperature ≥ current temperature",
                f"{max_t} < {current_temp}",
                ValidationStatus.ERROR,
                f"Maximum temperature ({max_t}°C) is less than current "
                f"temperature ({current_temp}°C).",
                "Verify the maximum thermometer reading."
            ))

    # ------------------------------------------------------------------
    # 8. Min Temperature ≤ Current Temperature
    # ------------------------------------------------------------------
    min_t = sec333_min if sec333_min is not None else min_temp

    if current_temp is not None and min_t is not None:
        if min_t <= current_temp:
            results.append(make_result(
                DOMAIN, "Min Temp ≤ Current Temp",
                f"Tmin={min_t}, Tcurr={current_temp}",
                "Minimum temperature ≤ current temperature",
                f"{min_t} ≤ {current_temp}", ValidationStatus.PASS,
                "Minimum temperature is correctly ≤ current temperature."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Min Temp ≤ Current Temp",
                f"Tmin={min_t}, Tcurr={current_temp}",
                "Minimum temperature ≤ current temperature",
                f"{min_t} > {current_temp}",
                ValidationStatus.ERROR,
                f"Minimum temperature ({min_t}°C) is greater than current "
                f"temperature ({current_temp}°C).",
                "Verify the minimum thermometer reading."
            ))

    # ------------------------------------------------------------------
    # 9. Max ≥ Min (if both present)
    # ------------------------------------------------------------------
    if max_t is not None and min_t is not None:
        if max_t >= min_t:
            results.append(make_result(
                DOMAIN, "Max Temp ≥ Min Temp",
                f"Tmax={max_t}, Tmin={min_t}",
                "Maximum ≥ Minimum temperature",
                f"{max_t} ≥ {min_t}", ValidationStatus.PASS,
                "Maximum temperature is correctly ≥ minimum temperature."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Max Temp ≥ Min Temp",
                f"Tmax={max_t}, Tmin={min_t}",
                "Maximum ≥ Minimum temperature",
                f"{max_t} < {min_t}",
                ValidationStatus.ERROR,
                f"Maximum temperature ({max_t}°C) is less than minimum "
                f"temperature ({min_t}°C).",
                "Check both extreme thermometers."
            ))

    # ------------------------------------------------------------------
    # 10. Current temperature between Max and Min (warning)
    # ------------------------------------------------------------------
    if current_temp is not None and max_t is not None and min_t is not None:
        if min_t <= current_temp <= max_t:
            results.append(make_result(
                DOMAIN, "Current Temp Within Max/Min Range",
                f"Tmin={min_t}, Tcurr={current_temp}, Tmax={max_t}",
                "Min ≤ Current ≤ Max",
                f"{min_t} ≤ {current_temp} ≤ {max_t}", ValidationStatus.PASS,
                "Current temperature lies between max and min as expected."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Current Temp Within Max/Min Range",
                f"Tmin={min_t}, Tcurr={current_temp}, Tmax={max_t}",
                "Min ≤ Current ≤ Max",
                f"Current={current_temp} outside [{min_t}, {max_t}]",
                ValidationStatus.WARNING,
                f"Current temperature ({current_temp}°C) lies outside the "
                f"max ({max_t}°C) / min ({min_t}°C) range. This is unusual "
                "but may occur if the observation time differs from the "
                "max/min recording period.",
                "Verify the max/min thermometer readings and observation timing."
            ))

    # ------------------------------------------------------------------
    # 11. Section 333 temperatures — range checks
    # ------------------------------------------------------------------
    if sec333_max is not None:
        results.append(_range_check(
            "Section 333 Max Temperature", sec333_max,
            TEMPERATURE_MIN, TEMPERATURE_MAX
        ))

    if sec333_min is not None:
        results.append(_range_check(
            "Section 333 Min Temperature", sec333_min,
            TEMPERATURE_MIN, TEMPERATURE_MAX
        ))

    # ------------------------------------------------------------------
    # 12. Section 555 soil / grass temps
    # ------------------------------------------------------------------
    for key, label in [
        ("sec555_grass_min_temp", "Grass Min Temperature"),
        ("sec555_soil_temp_5cm", "Soil Temp 5 cm"),
        ("sec555_soil_temp_10cm", "Soil Temp 10 cm"),
        ("sec555_soil_temp_20cm", "Soil Temp 20 cm"),
        ("sec555_soil_temp_30cm", "Soil Temp 30 cm"),
        ("sec555_soil_temp_50cm", "Soil Temp 50 cm"),
    ]:
        val = _to_float(data.get(key))
        if val is not None:
            # Soil temps have a narrower realistic range
            results.append(_range_check(label, val, -60.0, 80.0))

    # ------------------------------------------------------------------
    # 13. Thermograph Reading (optional) — range check
    # ------------------------------------------------------------------
    thermograph = _to_float(data.get("thermograph_reading"))
    if thermograph is not None:
        results.append(_range_check(
            "Thermograph Reading", thermograph,
            TEMPERATURE_MIN, TEMPERATURE_MAX
        ))

    # ------------------------------------------------------------------
    # 14. Hygrograph Reading (optional) — range check
    # ------------------------------------------------------------------
    hygrograph = _to_float(data.get("hygrograph_reading"))
    if hygrograph is not None:
        # Hygrograph measures relative humidity (0-100%)
        if 0.0 <= hygrograph <= 100.0:
            results.append(make_result(
                DOMAIN, "Hygrograph Reading Range", hygrograph,
                "0% to 100%", f"{hygrograph}%",
                ValidationStatus.PASS,
                f"Hygrograph reading ({hygrograph}%) is within the acceptable range."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Hygrograph Reading Range", hygrograph,
                "0% to 100%", f"{hygrograph}%",
                ValidationStatus.ERROR,
                f"Hygrograph reading ({hygrograph}%) is outside the acceptable "
                "range (0% to 100%).",
                "Verify the hygrograph instrument reading."
            ))

    return results


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _range_check(
    name: str, value: float, low: float, high: float
) -> ValidationResult:
    """Check that a temperature value falls within an acceptable range."""
    if low <= value <= high:
        return make_result(
            DOMAIN, f"{name} Range", value,
            f"{low}°C to {high}°C", f"{value}°C",
            ValidationStatus.PASS,
            f"{name} ({value}°C) is within the acceptable range."
        )
    else:
        return make_result(
            DOMAIN, f"{name} Range", value,
            f"{low}°C to {high}°C", f"{value}°C",
            ValidationStatus.ERROR,
            f"{name} ({value}°C) is outside the acceptable range "
            f"({low}°C to {high}°C).",
            f"Verify the thermometer reading. Expected {low} to {high}°C."
        )


def _precision_check(name: str, raw_value: Any) -> ValidationResult:
    """Warn if a temperature value has more than 1 decimal place."""
    if raw_value is None:
        return make_result(
            DOMAIN, f"{name} Precision", None, "1 decimal place",
            None, ValidationStatus.PASS,
            f"{name} precision check skipped (no value)."
        )

    raw_str = str(raw_value)
    if "." in raw_str:
        decimals = len(raw_str.split(".")[-1])
        if decimals > 1:
            return make_result(
                DOMAIN, f"{name} Precision", raw_value,
                "≤ 1 decimal place (tenths of °C)", f"{decimals} decimal places",
                ValidationStatus.WARNING,
                f"{name} has {decimals} decimal places. "
                "WMO FM-12 encodes temperature to the nearest 0.1°C.",
                f"Round {name} to one decimal place."
            )

    return make_result(
        DOMAIN, f"{name} Precision", raw_value,
        "≤ 1 decimal place", raw_str,
        ValidationStatus.PASS,
        f"{name} precision is acceptable."
    )


def _to_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
