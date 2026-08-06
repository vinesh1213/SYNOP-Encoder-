# =============================================================================
# SYNOP Validation Engine — Header Validator
# =============================================================================
# Requirement §1: Validates the structural header of a SYNOP message.
#   - AAXX report type identifier
#   - YYGGiw group (day, hour, wind indicator)
#   - IIiii (WMO station number)
#   - Mandatory group existence
#   - Message terminator '='
# =============================================================================

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import VALID_IW_CODES

logger = logging.getLogger(__name__)

DOMAIN = "header"


def validate_header(synop_string: str) -> List[ValidationResult]:
    """
    Validate the header portion of a SYNOP message string.

    Parameters
    ----------
    synop_string : str
        The complete raw SYNOP message (e.g. "AAXX 02094 43279 ...  =").

    Returns
    -------
    list[ValidationResult]
        One result per check performed.
    """
    results: List[ValidationResult] = []
    tokens = _tokenize(synop_string)

    # ------------------------------------------------------------------
    # 1. Report type must be AAXX
    # ------------------------------------------------------------------
    if not tokens:
        results.append(make_result(
            DOMAIN, "Report Type (AAXX)", synop_string, "First token must be 'AAXX'",
            "(empty)", ValidationStatus.ERROR,
            "SYNOP message is empty or could not be tokenized.",
            "Ensure the message starts with 'AAXX'."
        ))
        return results  # nothing more to validate

    report_type = tokens[0].upper()
    if report_type == "AAXX":
        results.append(make_result(
            DOMAIN, "Report Type (AAXX)", tokens[0], "'AAXX'",
            report_type, ValidationStatus.PASS,
            "Report type is AAXX — fixed land station surface report."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Report Type (AAXX)", tokens[0], "'AAXX'",
            report_type, ValidationStatus.ERROR,
            f"Expected 'AAXX' but found '{report_type}'. This is not a land surface SYNOP.",
            "Replace the first group with 'AAXX'."
        ))

    # ------------------------------------------------------------------
    # 2. YYGGiw group
    # ------------------------------------------------------------------
    if len(tokens) < 2:
        results.append(make_result(
            DOMAIN, "YYGGiw Group", None, "5-character YYGGiw group",
            "(missing)", ValidationStatus.ERROR,
            "YYGGiw group is missing from the header.",
            "Add a YYGGiw group after AAXX, e.g. '15064'."
        ))
    else:
        yyggiw = tokens[1]
        results.extend(_validate_yyggiw(yyggiw))

    # ------------------------------------------------------------------
    # 3. WMO station number (IIiii)
    # ------------------------------------------------------------------
    if len(tokens) < 3:
        results.append(make_result(
            DOMAIN, "Station Number (IIiii)", None, "5-digit WMO station number",
            "(missing)", ValidationStatus.ERROR,
            "WMO station number is missing.",
            "Add the 5-digit station identifier after the YYGGiw group."
        ))
    else:
        station = tokens[2]
        results.extend(_validate_station_number(station))

    # ------------------------------------------------------------------
    # 4. Mandatory groups exist (at minimum iRiXhVV and Nddff)
    # ------------------------------------------------------------------
    body_tokens = tokens[3:] if len(tokens) > 3 else []
    # Remove trailing '=' if present
    if body_tokens and body_tokens[-1] == "=":
        body_tokens = body_tokens[:-1]
    if body_tokens and body_tokens[-1].endswith("="):
        body_tokens[-1] = body_tokens[-1].rstrip("=")

    if len(body_tokens) < 2:
        results.append(make_result(
            DOMAIN, "Mandatory Groups", len(body_tokens), "At least iRiXhVV and Nddff groups",
            f"{len(body_tokens)} body group(s) found", ValidationStatus.ERROR,
            "SYNOP message must contain at least the iRiXhVV and Nddff groups.",
            "Ensure the observation data groups follow the station number."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Mandatory Groups", len(body_tokens), "≥ 2 body groups",
            f"{len(body_tokens)} body group(s) found", ValidationStatus.PASS,
            "Minimum mandatory groups are present."
        ))

    # ------------------------------------------------------------------
    # 5. Message terminator '='
    # ------------------------------------------------------------------
    raw_stripped = synop_string.strip()
    if raw_stripped.endswith("="):
        results.append(make_result(
            DOMAIN, "Message Terminator", "=", "Message ends with '='",
            "=", ValidationStatus.PASS,
            "Message correctly terminates with '='."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Message Terminator", raw_stripped[-1:] if raw_stripped else "(empty)",
            "Message ends with '='",
            raw_stripped[-1:], ValidationStatus.WARNING,
            "SYNOP message should end with the '=' terminator.",
            "Append '=' at the end of the message."
        ))

    return results


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _tokenize(synop_string: str) -> List[str]:
    """Split SYNOP into whitespace-separated tokens, preserving '='."""
    cleaned = synop_string.replace("\n", " ").replace("\r", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.split() if cleaned else []


def _validate_yyggiw(group: str) -> List[ValidationResult]:
    """Validate the YYGGiw date/time/wind-indicator group."""
    results: List[ValidationResult] = []

    if len(group) != 5:
        results.append(make_result(
            DOMAIN, "YYGGiw Length", group, "Exactly 5 characters",
            f"{len(group)} characters", ValidationStatus.ERROR,
            f"YYGGiw group '{group}' must be exactly 5 characters.",
            "Format: DDHHW where DD=day, HH=hour, W=wind indicator."
        ))
        return results

    yy = group[0:2]
    gg = group[2:4]
    iw = group[4]

    # Day of month (YY)
    if yy == "//":
        results.append(make_result(
            DOMAIN, "Day of Month (YY)", yy, "01–31 or '//'",
            yy, ValidationStatus.WARNING,
            "Day of month is missing (//).",
            "Report the day of observation if available."
        ))
    elif yy.isdigit():
        day = int(yy)
        if 1 <= day <= 31:
            results.append(make_result(
                DOMAIN, "Day of Month (YY)", yy, "01–31",
                day, ValidationStatus.PASS,
                f"Day of month: {day}."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Day of Month (YY)", yy, "01–31",
                day, ValidationStatus.ERROR,
                f"Day '{day}' is out of range (must be 01–31).",
                "Correct the day of the month."
            ))
    else:
        results.append(make_result(
            DOMAIN, "Day of Month (YY)", yy, "01–31 (digits) or '//'",
            yy, ValidationStatus.ERROR,
            f"Day of month '{yy}' is not numeric.",
            "Use two digits for the day (01–31) or '//' if unknown."
        ))

    # Hour (GG)
    if gg == "//":
        results.append(make_result(
            DOMAIN, "Hour (GG)", gg, "00–23 or '//'",
            gg, ValidationStatus.WARNING,
            "Hour of observation is missing (//).",
            "Report the hour of observation if available."
        ))
    elif gg.isdigit():
        hour = int(gg)
        if 0 <= hour <= 23:
            results.append(make_result(
                DOMAIN, "Hour (GG)", gg, "00–23",
                hour, ValidationStatus.PASS,
                f"Hour of observation: {hour:02d} UTC."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Hour (GG)", gg, "00–23",
                hour, ValidationStatus.ERROR,
                f"Hour '{hour}' is out of range (must be 00–23).",
                "Correct the UTC hour of observation."
            ))
    else:
        results.append(make_result(
            DOMAIN, "Hour (GG)", gg, "00–23 (digits) or '//'",
            gg, ValidationStatus.ERROR,
            f"Hour '{gg}' is not numeric.",
            "Use two digits for the hour (00–23) or '//' if unknown."
        ))

    # Wind speed indicator (iw)
    if iw in VALID_IW_CODES:
        results.append(make_result(
            DOMAIN, "Wind Indicator (iw)", iw, "0, 1, 3, or 4",
            iw, ValidationStatus.PASS,
            f"Wind indicator: {iw} — " + (
                "m/s" if iw in ("0", "1") else "knots"
            ) + " (" + ("estimated" if iw in ("0", "3") else "anemometer") + ")."
        ))
    elif iw == "/":
        results.append(make_result(
            DOMAIN, "Wind Indicator (iw)", iw, "0, 1, 3, or 4",
            iw, ValidationStatus.WARNING,
            "Wind indicator is missing (/).",
            "Specify the wind speed unit indicator."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Wind Indicator (iw)", iw, "0, 1, 3, or 4",
            iw, ValidationStatus.ERROR,
            f"Wind indicator '{iw}' is invalid.",
            "Use 0 or 1 for m/s, 3 or 4 for knots."
        ))

    return results


def _validate_station_number(station: str) -> List[ValidationResult]:
    """Validate the 5-digit WMO station number (IIiii)."""
    results: List[ValidationResult] = []

    if len(station) != 5:
        results.append(make_result(
            DOMAIN, "Station Number Length", station, "Exactly 5 digits",
            f"{len(station)} characters", ValidationStatus.ERROR,
            f"Station number '{station}' must be exactly 5 digits.",
            "Use the full 5-digit WMO station identifier (IIiii)."
        ))
        return results

    if station.isdigit():
        # WMO block numbers (II) range from 01–98 typically
        block = int(station[0:2])
        if block == 0 or block > 98:
            results.append(make_result(
                DOMAIN, "Station Block Number", station, "WMO block 01–98",
                block, ValidationStatus.WARNING,
                f"WMO block number '{block:02d}' is unusual (expected 01–98).",
                "Verify the station identifier."
            ))
        else:
            results.append(make_result(
                DOMAIN, "Station Number (IIiii)", station, "5-digit WMO identifier",
                station, ValidationStatus.PASS,
                f"Station number {station} (block {block:02d})."
            ))
    elif station == "/////":
        results.append(make_result(
            DOMAIN, "Station Number (IIiii)", station, "5-digit WMO identifier",
            station, ValidationStatus.WARNING,
            "Station number is missing (/////).",
            "Provide the station's WMO identifier."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Station Number (IIiii)", station, "5-digit numeric identifier",
            station, ValidationStatus.ERROR,
            f"Station number '{station}' contains non-digit characters.",
            "Use only digits for the station number."
        ))

    return results
