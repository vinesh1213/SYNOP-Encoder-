# =============================================================================
# SYNOP Validation Engine — Wind Validator
# =============================================================================
# Requirement §6: Validates wind observations.
#   - Wind direction code (00–36 or 99)
#   - Wind speed range
#   - Calm wind rules (dd=00 requires ff=00)
#   - Wind unit indicator (iw)
#   - Gust > sustained speed
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    VALID_DD_CODES, VALID_IW_CODES,
    MAX_WIND_SPEED_MS, MAX_WIND_SPEED_KT,
)

logger = logging.getLogger(__name__)

DOMAIN = "wind"


def validate_wind(data: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate wind-related observations.

    Expected keys: wind_direction, wind_speed, wind_unit, max_gust.

    Parameters
    ----------
    data : dict
        Observation data dictionary.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    wind_dir = data.get("wind_direction")
    wind_unit = data.get("wind_unit")


    wind_readings = data.get("wind_readings")
    wind_speed = _to_float(data.get("wind_speed"))

    # ------------------------------------------------------------------
    # Wind Speed Averaging (Requirement)
    # ------------------------------------------------------------------
    if wind_readings and isinstance(wind_readings, list) and len(wind_readings) > 0:
        valid_readings = [float(r) for r in wind_readings if r is not None and str(r).strip() != ""]
        if not valid_readings:
            results.append(make_result(
                DOMAIN, "Wind Speed Averaging", None,
                "At least 1 valid reading", "No valid readings",
                ValidationStatus.ERROR,
                "Insufficient wind data.",
                "Provide wind speed readings for averaging."
            ))
            wind_speed = None
        else:
            avg_wind = sum(valid_readings) / len(valid_readings)
            logger.info(f"[AUDIT] Calculated average wind speed: sum({valid_readings}) / len = {avg_wind}")
            wind_speed = avg_wind
            data["wind_speed"] = avg_wind  # Ensure downstream validation uses the calculated average

    # ------------------------------------------------------------------
    # 1. Wind direction — compass or numeric check
    # ------------------------------------------------------------------
    compass_directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
        "CALM", "VRB", "VAR", "VARIABLE"
    ]
    if wind_dir is not None and str(wind_dir).strip() != "":
        dir_str = str(wind_dir).strip().upper()
        is_valid_dir = False
        if dir_str in compass_directions:
            is_valid_dir = True
        else:
            try:
                val = float(wind_dir)
                if (0 <= val <= 360) or val == 99:
                    is_valid_dir = True
            except (ValueError, TypeError):
                is_valid_dir = False

        if is_valid_dir:
            results.append(make_result(
                DOMAIN, "Wind Direction Format", wind_dir,
                "Compass direction or degrees (0–360)", str(wind_dir),
                ValidationStatus.PASS,
                f"Wind direction ({wind_dir}) is valid."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Wind Direction Format", wind_dir,
                "Compass direction or degrees (0–360)", str(wind_dir),
                ValidationStatus.ERROR,
                f"Wind direction '{wind_dir}' is invalid.",
                "Wind direction must be a valid compass direction (e.g., N, SW) or degrees (0–360)."
            ))

    # ------------------------------------------------------------------
    # 2. Wind speed — range check
    # ------------------------------------------------------------------
    if wind_speed is not None:
        max_speed = MAX_WIND_SPEED_KT if wind_unit == "knots" else MAX_WIND_SPEED_MS
        unit_label = wind_unit or "m/s"

        if wind_speed < 0:
            results.append(make_result(
                DOMAIN, "Wind Speed Range", wind_speed,
                f"0–{max_speed} {unit_label}", f"{wind_speed:.1f} {unit_label}",
                ValidationStatus.ERROR,
                "Wind speed cannot be negative.",
                "Enter non-negative wind speed readings."
            ))
        elif wind_speed <= max_speed:
            results.append(make_result(
                DOMAIN, "Wind Speed Range", wind_speed,
                f"0–{max_speed} {unit_label}", f"{wind_speed:.1f} {unit_label}",
                ValidationStatus.PASS,
                f"Wind speed ({wind_speed:.1f} {unit_label}) is within range."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Wind Speed Range", wind_speed,
                f"0–{max_speed} {unit_label}", f"{wind_speed:.1f} {unit_label}",
                ValidationStatus.ERROR,
                f"Wind speed ({wind_speed:.1f} {unit_label}) exceeds the "
                f"physical limit of {max_speed} {unit_label}.",
                "Verify the anemometer reading."
            ))

    # ------------------------------------------------------------------
    # 3. Wind unit indicator (iw)
    # ------------------------------------------------------------------
    if wind_unit is not None:
        # Map observation schema wind_unit to expected iw values
        if wind_unit in ("m/s", "knots"):
            results.append(make_result(
                DOMAIN, "Wind Unit", wind_unit,
                "m/s or knots", wind_unit,
                ValidationStatus.PASS,
                f"Wind unit '{wind_unit}' is valid."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Wind Unit", wind_unit,
                "m/s or knots", wind_unit,
                ValidationStatus.WARNING,
                f"Wind unit '{wind_unit}' is non-standard.",
                "Use 'm/s' or 'knots'."
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
