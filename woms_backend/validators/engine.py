# =============================================================================
# SYNOP Validation Engine — Central Orchestrator
# =============================================================================
# Requirements §14–16: Orchestrates all validators, enforces WMO code tables,
# handles errors, and builds the final validation report.
#
# Two entry points:
#   1. validate_observation(data, station_number) — from observation dict
#   2. validate_synop_string(synop) — from raw SYNOP string
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validators.models import (
    ValidationResult, ValidationReport, ValidationStatus, ReportStatus,
)
from validators.header_validator import validate_header
from validators.group_format_validator import validate_group_formats
from validators.temperature_validator import validate_temperature
from validators.humidity_validator import validate_humidity
from validators.pressure_validator import validate_pressure
from validators.wind_validator import validate_wind
from validators.visibility_validator import validate_visibility
from validators.cloud_validator import validate_clouds
from validators.weather_validator import validate_weather
from validators.rainfall_validator import validate_rainfall
from validators.temporal_validator import validate_temporal
from validators.sensor_validator import validate_sensors
from validators.cross_parameter_validator import validate_cross_parameters

logger = logging.getLogger(__name__)


class SynopValidationEngine:
    """
    Central orchestrator for the SYNOP Validation Engine.

    Runs all validators in the correct order, collects results, and
    builds a structured ValidationReport.

    Usage
    -----
    >>> engine = SynopValidationEngine()
    >>> report = engine.validate_observation(obs_data, station_number="43279")
    >>> print(report.to_dict())
    """

    # Domains in execution order — used for consistent summary ordering
    DOMAIN_ORDER = [
        "header",
        "group_format",
        "station",
        "sensor",
        "temperature",
        "humidity",
        "pressure",
        "wind",
        "visibility",
        "clouds",
        "weather",
        "rainfall",
        "temporal",
        "cross_parameter",
    ]

    def validate_observation(
        self,
        data: Dict[str, Any],
        station_number: Optional[str] = None,
        station_info: Optional[Dict[str, Any]] = None,
        previous_observation: Optional[Dict[str, Any]] = None,
        existing_observations: Optional[List[Dict[str, Any]]] = None,
        generated_synop: Optional[str] = None,
    ) -> ValidationReport:
        """
        Validate an observation from its data dictionary (pre-encoding).

        This is the primary validation path when an observer submits data
        through the WOMS frontend.

        Parameters
        ----------
        data : dict
            Observation data matching ObservationSchema fields.
        station_number : str or None
            5-digit WMO station number.
        station_info : dict or None
            Station metadata (is_active, elevation, etc.).
        previous_observation : dict or None
            Previous observation for temporal consistency.
        existing_observations : list or None
            Existing observations for duplicate detection.
        generated_synop : str or None
            The generated SYNOP string (for structural validation).

        Returns
        -------
        ValidationReport
        """
        all_results: List[ValidationResult] = []

        logger.info(
            "Starting observation validation for station %s",
            station_number or "(unknown)"
        )

        # ---- 1. Header / SYNOP string validation (if available) ----
        if generated_synop:
            all_results.extend(validate_header(generated_synop))
            all_results.extend(validate_group_formats(generated_synop))
        elif data.get("generated_synop"):
            synop = str(data["generated_synop"])
            all_results.extend(validate_header(synop))
            all_results.extend(validate_group_formats(synop))

        # ---- 2. Station / Sensor validation ----
        all_results.extend(
            validate_sensors(data, station_info, existing_observations)
        )

        # ---- 3. Temperature validation ----
        all_results.extend(validate_temperature(data))

        # ---- 4. Humidity validation ----
        all_results.extend(validate_humidity(data))

        # ---- 5. Pressure validation ----
        all_results.extend(validate_pressure(data))

        # ---- 6. Wind validation ----
        all_results.extend(validate_wind(data))

        # ---- 7. Visibility validation ----
        all_results.extend(validate_visibility(data))

        # ---- 8. Cloud validation ----
        all_results.extend(validate_clouds(data))

        # ---- 9. Weather validation ----
        all_results.extend(validate_weather(data))

        # ---- 10. Rainfall validation ----
        all_results.extend(validate_rainfall(data))

        # ---- 11. Temporal consistency ----
        all_results.extend(validate_temporal(data, previous_observation))

        # ---- 12. Cross-parameter validation ----
        elevation = None
        if station_info:
            elevation = station_info.get("elevation")
        all_results.extend(validate_cross_parameters(data, elevation))

        # ---- Build report ----
        report = self._build_report(all_results)

        logger.info(
            "Validation complete: %s (score=%.1f, checks=%d, pass=%d, warn=%d, err=%d)",
            report.status.value, report.overall_score,
            report.total_checks, report.passed, report.warnings, report.errors,
        )

        return report

    def validate_synop_string(
        self,
        synop_string: str,
        station_info: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """
        Validate a raw SYNOP message string.

        This path is used when receiving or decoding an external SYNOP
        bulletin. It performs structural + code-table validation but
        cannot do all meteorological cross-checks (since the decoded
        values need more context).

        Parameters
        ----------
        synop_string : str
            Raw SYNOP string (e.g. "AAXX 02094 43279 31/56 ... =").
        station_info : dict or None
            Optional station metadata.

        Returns
        -------
        ValidationReport
        """
        all_results: List[ValidationResult] = []

        logger.info("Starting SYNOP string validation")

        # ---- 1. Header validation ----
        all_results.extend(validate_header(synop_string))

        # ---- 2. Group format validation ----
        all_results.extend(validate_group_formats(synop_string))

        # ---- 3. Decode values for meteorological checks ----
        decoded = self._decode_for_validation(synop_string)

        if decoded:
            all_results.extend(validate_temperature(decoded))
            all_results.extend(validate_humidity(decoded))
            all_results.extend(validate_pressure(decoded))
            all_results.extend(validate_wind(decoded))
            all_results.extend(validate_visibility(decoded))
            all_results.extend(validate_clouds(decoded))
            all_results.extend(validate_weather(decoded))
            all_results.extend(validate_rainfall(decoded))
            all_results.extend(validate_cross_parameters(
                decoded,
                station_info.get("elevation") if station_info else None,
            ))

        # ---- Build report ----
        report = self._build_report(all_results)

        logger.info(
            "SYNOP string validation complete: %s (score=%.1f)",
            report.status.value, report.overall_score,
        )

        return report

    # ===================================================================
    # Internal methods
    # ===================================================================

    def _build_report(self, results: List[ValidationResult]) -> ValidationReport:
        """Aggregate individual results into a final ValidationReport."""
        report = ValidationReport()
        report.total_checks = len(results)

        # Count by status
        for r in results:
            if r.status == ValidationStatus.PASS:
                report.passed += 1
            elif r.status == ValidationStatus.WARNING:
                report.warnings += 1
                report.warnings_list.append(r.to_dict())
            elif r.status == ValidationStatus.ERROR:
                report.errors += 1
                report.errors_list.append(r.to_dict())

            report.all_results.append(r.to_dict())

        # Overall score
        if report.total_checks > 0:
            report.overall_score = (report.passed / report.total_checks) * 100.0
        else:
            report.overall_score = 100.0

        # Overall status
        if report.errors > 0:
            report.status = ReportStatus.REJECTED
        elif report.warnings > 0:
            report.status = ReportStatus.WARNING
        else:
            report.status = ReportStatus.ACCEPTED

        # Per-domain summary
        domain_statuses: Dict[str, str] = {}
        for r in results:
            domain = r.domain or "other"
            # Initialize domain as PASS if not yet seen
            if domain not in domain_statuses:
                domain_statuses[domain] = "PASS"
            current = domain_statuses[domain]
            if r.status == ValidationStatus.ERROR:
                domain_statuses[domain] = "ERROR"
            elif r.status == ValidationStatus.WARNING and current != "ERROR":
                domain_statuses[domain] = "WARNING"
            # PASS doesn't override WARNING or ERROR

        # Ensure consistent ordering
        for d in self.DOMAIN_ORDER:
            if d in domain_statuses:
                report.validation_summary[d] = domain_statuses[d]
        # Add any domains not in the predefined order
        for d, s in domain_statuses.items():
            if d not in report.validation_summary:
                report.validation_summary[d] = s

        return report

    def _decode_for_validation(self, synop_string: str) -> Optional[Dict[str, Any]]:
        """
        Minimally decode a SYNOP string to extract values for
        meteorological validation.

        This is a lightweight decoder focused on extracting enough data
        for the validators. It does NOT replace the full SynopDecoder.
        """
        try:
            tokens = synop_string.replace("\n", " ").strip().split()

            # Remove terminator
            if tokens and tokens[-1] == "=":
                tokens = tokens[:-1]
            if tokens and tokens[-1].endswith("="):
                tokens[-1] = tokens[-1].rstrip("=")

            if len(tokens) < 4:
                return None

            # Extract wind indicator from header
            yyggiw = tokens[1] if len(tokens) > 1 else ""
            iw = yyggiw[4] if len(yyggiw) >= 5 else "1"

            # Split body into sections
            body = tokens[3:]
            sec1, sec3, sec5 = [], [], []
            current = sec1
            for t in body:
                if t == "333":
                    current = sec3
                    continue
                if t in ("555", "55555"):
                    current = sec5
                    continue
                current.append(t)

            data: Dict[str, Any] = {}

            # Wind unit
            data["wind_unit"] = "knots" if iw in ("3", "4") else "m/s"

            # Parse Section 1 groups
            if len(sec1) >= 1 and len(sec1[0]) == 5:
                # iRiXhVV
                vv = sec1[0][3:5]
                if vv.isdigit():
                    data["visibility"] = self._decode_vv_to_km(int(vv))
                    data["visibility_unit"] = "km"

            if len(sec1) >= 2 and len(sec1[1]) == 5:
                # Nddff
                n = sec1[1][0]
                dd = sec1[1][1:3]
                ff = sec1[1][3:5]

                if n.isdigit():
                    data["total_cloud_cover"] = int(n)

                if dd.isdigit():
                    data["wind_direction"] = int(dd) * 10

                if ff.isdigit():
                    data["wind_speed"] = int(ff)

            for g in sec1[2:]:
                if len(g) != 5:
                    continue

                if g[0] == "1" and g[1] in ("0", "1") and g[2:5].isdigit():
                    sign = 1 if g[1] == "0" else -1
                    data["dry_bulb"] = sign * int(g[2:5]) / 10.0

                elif g[0] == "2" and g[1] in ("0", "1") and g[2:5].isdigit():
                    sign = 1 if g[1] == "0" else -1
                    data["dew_point"] = sign * int(g[2:5]) / 10.0

                elif g[0] == "3" and g[1:5].isdigit():
                    val = int(g[1:5])
                    if val < 5000:
                        val += 10000
                    data["station_pressure"] = val / 10.0

                elif g[0] == "4" and g[1:5].isdigit():
                    val = int(g[1:5])
                    if val < 5000:
                        val += 10000
                    data["msl_pressure"] = val / 10.0

                elif g[0] == "5" and g[1].isdigit() and g[2:5].isdigit():
                    data["pressure_tendency"] = int(g[1])
                    data["pressure_change"] = int(g[2:5]) / 10.0

                elif g[0] == "6" and g[1:4].isdigit():
                    rrr = int(g[1:4])
                    if rrr == 990:
                        data["rainfall"] = 0.0  # trace
                    else:
                        data["rainfall"] = float(rrr)
                    if g[4].isdigit():
                        data["rain_duration"] = int(g[4])

                elif g[0] == "7" and g[1:3].isdigit():
                    data["present_weather"] = int(g[1:3])
                    if g[3].isdigit():
                        data["past_weather_1"] = int(g[3])
                    if g[4].isdigit():
                        data["past_weather_2"] = int(g[4])

                elif g[0] == "8":
                    if g[1].isdigit():
                        data["low_cloud_amount"] = int(g[1])
                    if g[2].isdigit():
                        data["low_cloud_type"] = int(g[2])
                    if g[3].isdigit():
                        data["middle_cloud_type"] = int(g[3])
                    if g[4].isdigit():
                        data["high_cloud_type"] = int(g[4])

            # Parse Section 333
            for g in sec3:
                if len(g) == 5:
                    if g[0] == "1" and g[1] in ("0", "1") and g[2:5].isdigit():
                        sign = 1 if g[1] == "0" else -1
                        data["sec333_max_temperature"] = sign * int(g[2:5]) / 10.0

                    elif g[0] == "2" and g[1] in ("0", "1") and g[2:5].isdigit():
                        sign = 1 if g[1] == "0" else -1
                        data["sec333_min_temperature"] = sign * int(g[2:5]) / 10.0

                    elif g[0] == "3" and g[1].isdigit():
                        data["ground_state"] = int(g[1])

                    elif g[0] == "5" and g[1:4].isdigit():
                        data["sunshine_hours"] = int(g[1:4]) / 10.0
                        
                    elif g[0] == "6" and g[1:4].isdigit():
                        rrr = int(g[1:4])
                        if rrr == 990:
                            data["rainfall_24h"] = 0.0
                        else:
                            data["rainfall_24h"] = float(rrr)

            return data

        except Exception as e:
            logger.warning("Failed to decode SYNOP for validation: %s", e)
            return None

    @staticmethod
    def _decode_vv_to_km(vv: int) -> float:
        """Decode VV code to visibility in km."""
        if vv == 0:
            return 0.05
        elif 1 <= vv <= 50:
            return vv / 10.0
        elif 56 <= vv <= 80:
            return float(vv - 50)
        elif 81 <= vv <= 88:
            return 35.0 + (vv - 80) * 5.0
        elif vv == 89:
            return 70.0
        elif 90 <= vv <= 99:
            special_km = {
                90: 0.025, 91: 0.05, 92: 0.2, 93: 0.5,
                94: 1.0, 95: 2.0, 96: 4.0, 97: 10.0,
                98: 20.0, 99: 50.0,
            }
            return special_km.get(vv, 0.0)
        return 0.0
