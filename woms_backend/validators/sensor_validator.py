# =============================================================================
# SYNOP Validation Engine — Sensor Validator
# =============================================================================
# Requirement §12: Validates sensor and station health.
#   - Sensor availability (which parameters are reported)
#   - Missing observations (all critical fields None)
#   - Duplicate observation detection
#   - Station active status
#   - Calibration status (stub for future metadata)
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result

logger = logging.getLogger(__name__)

DOMAIN = "sensor"

# Critical meteorological fields that should be present in a valid observation
CRITICAL_FIELDS = [
    "dry_bulb",
    "station_pressure",
    "wind_direction",
    "wind_speed",
    "total_cloud_cover",
    "visibility",
]

# Important but not critical
IMPORTANT_FIELDS = [
    "wet_bulb",
    "dew_point",
    "msl_pressure",
    "present_weather",
]

# Section 1 encoded data fields
ALL_SENSOR_FIELDS = CRITICAL_FIELDS + IMPORTANT_FIELDS + [
    "past_weather_1",
    "past_weather_2",
    "low_cloud_amount",
    "low_cloud_type",
    "middle_cloud_type",
    "high_cloud_type",
    "lowest_cloud_base",
    "pressure_tendency",
    "pressure_change",
    "rainfall",
]


def validate_sensors(
    data: Dict[str, Any],
    station_info: Optional[Dict[str, Any]] = None,
    existing_observations: Optional[List[Dict[str, Any]]] = None,
) -> List[ValidationResult]:
    """
    Validate sensor availability, station status, and detect duplicates.

    Parameters
    ----------
    data : dict
        Current observation data.
    station_info : dict or None
        Station metadata (is_active, station_type, etc.).
    existing_observations : list or None
        List of existing observation dicts for the same station
        (used for duplicate detection).

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    # ------------------------------------------------------------------
    # 1. Station active status
    # ------------------------------------------------------------------
    if station_info is not None:
        is_active = station_info.get("is_active", True)
        if is_active:
            results.append(make_result(
                DOMAIN, "Station Active Status", True,
                "Station should be active", "Active",
                ValidationStatus.PASS,
                "Station is active."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Station Active Status", False,
                "Station should be active", "Inactive",
                ValidationStatus.WARNING,
                "Station is marked as inactive. Observations from inactive "
                "stations may not be distributed.",
                "Verify station status or reactivate the station."
            ))

    # ------------------------------------------------------------------
    # 2. Sensor availability — critical fields
    # ------------------------------------------------------------------
    missing_critical = []
    for field in CRITICAL_FIELDS:
        val = data.get(field)
        if val is None or val == "" or val == "//":
            missing_critical.append(field)

    if not missing_critical:
        results.append(make_result(
            DOMAIN, "Critical Sensors", len(CRITICAL_FIELDS),
            "All critical fields present",
            f"{len(CRITICAL_FIELDS)}/{len(CRITICAL_FIELDS)} present",
            ValidationStatus.PASS,
            "All critical meteorological sensors are reporting."
        ))
    elif len(missing_critical) <= 2:
        results.append(make_result(
            DOMAIN, "Critical Sensors", missing_critical,
            "All critical fields present",
            f"{len(CRITICAL_FIELDS) - len(missing_critical)}/{len(CRITICAL_FIELDS)} present",
            ValidationStatus.WARNING,
            f"Missing critical field(s): {', '.join(missing_critical)}. "
            "Some sensors may be offline or readings unavailable.",
            "Check the listed sensors and report values if available."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Critical Sensors", missing_critical,
            "All critical fields present",
            f"{len(CRITICAL_FIELDS) - len(missing_critical)}/{len(CRITICAL_FIELDS)} present",
            ValidationStatus.ERROR,
            f"Multiple critical fields are missing: {', '.join(missing_critical)}. "
            "The observation may be too incomplete for a valid SYNOP.",
            "Check all instruments. A minimum of dry bulb, pressure, wind, "
            "cloud cover, and visibility are needed."
        ))

    # ------------------------------------------------------------------
    # 3. Sensor availability — important fields
    # ------------------------------------------------------------------
    missing_important = []
    for field in IMPORTANT_FIELDS:
        val = data.get(field)
        if val is None or val == "" or val == "//":
            missing_important.append(field)

    if missing_important:
        results.append(make_result(
            DOMAIN, "Important Sensors", missing_important,
            "All important fields present",
            f"{len(IMPORTANT_FIELDS) - len(missing_important)}/{len(IMPORTANT_FIELDS)} present",
            ValidationStatus.WARNING,
            f"Missing important field(s): {', '.join(missing_important)}. "
            "The SYNOP will have reduced data content.",
            "Report these values if instruments are available."
        ))

    # ------------------------------------------------------------------
    # 4. Completely empty observation
    # ------------------------------------------------------------------
    all_none = all(
        data.get(f) is None or data.get(f) == ""
        for f in ALL_SENSOR_FIELDS
    )
    if all_none:
        results.append(make_result(
            DOMAIN, "Empty Observation", True,
            "At least one meteorological field should have data",
            "All fields empty",
            ValidationStatus.ERROR,
            "All meteorological data fields are empty. "
            "This observation contains no usable data.",
            "Ensure at least temperature, pressure, and wind are recorded."
        ))

    # ------------------------------------------------------------------
    # 5. Duplicate observation detection
    # ------------------------------------------------------------------
    if existing_observations:
        obs_date = data.get("observation_date")
        obs_time = data.get("observation_time")

        for existing in existing_observations:
            if (
                existing.get("observation_date") == obs_date
                and existing.get("observation_time") == obs_time
            ):
                results.append(make_result(
                    DOMAIN, "Duplicate Observation",
                    f"Date={obs_date}, Time={obs_time}",
                    "No duplicate observations for same station/date/time",
                    "Duplicate found",
                    ValidationStatus.WARNING,
                    f"An observation already exists for this station at "
                    f"{obs_date} {obs_time}. This may be a duplicate.",
                    "Verify this is not a duplicate submission."
                ))
                break
        else:
            results.append(make_result(
                DOMAIN, "Duplicate Check", f"Date={obs_date}, Time={obs_time}",
                "No duplicates", "No duplicate found",
                ValidationStatus.PASS,
                "No duplicate observation detected."
            ))

    # ------------------------------------------------------------------
    # 6. Observation metadata
    # ------------------------------------------------------------------
    if not data.get("observer_name") or not str(data.get("observer_name")).strip():
        results.append(make_result(
            DOMAIN, "Observer Name", data.get("observer_name"),
            "Observer name should be recorded",
            str(data.get("observer_name", "(empty)")),
            ValidationStatus.WARNING,
            "Observer name is missing.",
            "Record the name of the observer or 'AUTO' for automatic stations."
        ))

    if not data.get("observation_date"):
        results.append(make_result(
            DOMAIN, "Observation Date", None,
            "Observation date is required", "(missing)",
            ValidationStatus.ERROR,
            "Observation date is missing.",
            "Enter the date of the observation (YYYY-MM-DD)."
        ))

    if not data.get("observation_time"):
        results.append(make_result(
            DOMAIN, "Observation Time", None,
            "Observation time is required", "(missing)",
            ValidationStatus.ERROR,
            "Observation time is missing.",
            "Enter the UTC time of the observation (HH:MM)."
        ))

    # ------------------------------------------------------------------
    # 7. Calibration status (stub — ready for future metadata)
    # ------------------------------------------------------------------
    # When calibration metadata is available, it would be checked here.
    # For now, this is a placeholder that always passes.
    if station_info and station_info.get("last_calibration_date"):
        # Future: compare calibration date with threshold
        results.append(make_result(
            DOMAIN, "Calibration Status",
            station_info.get("last_calibration_date"),
            "Calibration within 12 months",
            str(station_info.get("last_calibration_date")),
            ValidationStatus.PASS,
            "Calibration status is available."
        ))

    return results
