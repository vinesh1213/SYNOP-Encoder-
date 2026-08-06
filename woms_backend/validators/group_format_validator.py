# =============================================================================
# SYNOP Validation Engine — Group Format Validator
# =============================================================================
# Requirement §2: Validates the structural format of every SYNOP group
# according to WMO FM-12 specification.  This is purely structural — it
# checks character-level patterns, not meteorological plausibility.
# =============================================================================

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from validators.models import ValidationResult, ValidationStatus, make_result
from validators.wmo_code_tables import (
    VALID_IR_CODES, VALID_IX_CODES, VALID_H_CODES,
    VALID_N_CODES, VALID_A_CODES, VALID_TR_CODES,
    VALID_CL_CODES, VALID_CM_CODES, VALID_CH_CODES,
    VALID_NH_CODES, VALID_W_CODES,
)

logger = logging.getLogger(__name__)

DOMAIN = "group_format"

# Regex helpers — a single SYNOP digit or '/'
_D = r"[\d/]"


def validate_group_formats(synop_string: str) -> List[ValidationResult]:
    """
    Validate the structural format of every group in a SYNOP message.

    This function splits the SYNOP into its sections and checks each group
    against the expected character patterns defined in WMO FM-12.

    Parameters
    ----------
    synop_string : str
        The complete raw SYNOP message.

    Returns
    -------
    list[ValidationResult]
    """
    results: List[ValidationResult] = []

    tokens = _tokenize(synop_string)
    if len(tokens) < 4:
        # Header validator already flags this; skip format checks.
        return results

    # Strip header (AAXX, YYGGiw, IIiii) and terminator
    body = tokens[3:]
    if body and body[-1] == "=":
        body = body[:-1]
    if body and body[-1].endswith("="):
        body[-1] = body[-1].rstrip("=")

    # Split into sections
    sec1, sec3, sec5 = _split_sections(body)

    # ---- Section 1 groups ----
    if len(sec1) >= 1:
        results.extend(_validate_irixhvv(sec1[0]))
    if len(sec1) >= 2:
        results.extend(_validate_nddff(sec1[1]))

    for group in sec1[2:]:
        if len(group) != 5:
            results.append(make_result(
                DOMAIN, "Section 1 Group Length", group,
                "5 characters per group", f"{len(group)} chars",
                ValidationStatus.WARNING,
                f"Section 1 group '{group}' is not 5 characters long.",
                "Each Section 1 data group should be exactly 5 characters."
            ))
            continue

        prefix = group[0]
        if prefix == "1":
            results.extend(_validate_1snttt(group))
        elif prefix == "2":
            results.extend(_validate_2snttt(group))
        elif prefix == "3":
            results.extend(_validate_3pppp(group))
        elif prefix == "4":
            results.extend(_validate_4pppp(group))
        elif prefix == "5":
            results.extend(_validate_5appp(group))
        elif prefix == "6":
            results.extend(_validate_6rrrt(group))
        elif prefix == "7":
            results.extend(_validate_7www(group))
        elif prefix == "8":
            results.extend(_validate_8cloud(group))
        elif prefix == "9":
            results.extend(_validate_9gust(group))

    # ---- Section 333 groups ----
    for group in sec3:
        if len(group) != 5:
            if len(group) == 4:
                # Some Section 333 groups are 4 characters (e.g. E'sss)
                pass
            else:
                results.append(make_result(
                    DOMAIN, "Section 333 Group Length", group,
                    "4–5 characters", f"{len(group)} chars",
                    ValidationStatus.WARNING,
                    f"Section 333 group '{group}' has unexpected length.",
                ))
        # Section 333 uses the same numeric-prefix convention for many groups.
        # We do a lightweight format check.
        results.extend(_validate_sec333_group(group))

    # ---- Section 555 groups ----
    for group in sec5:
        results.extend(_validate_sec555_group(group))

    return results


# -----------------------------------------------------------------------
# Section splitter
# -----------------------------------------------------------------------

def _split_sections(body: List[str]):
    """Split the body tokens into Section 1, Section 333, Section 555."""
    sec1, sec3, sec5 = [], [], []
    current = sec1

    for token in body:
        if token == "333":
            current = sec3
            continue
        if token in ("555", "55555"):
            current = sec5
            continue
        current.append(token)

    return sec1, sec3, sec5


# -----------------------------------------------------------------------
# Individual group validators (Section 1)
# -----------------------------------------------------------------------

def _validate_irixhvv(group: str) -> List[ValidationResult]:
    """Validate iRiXhVV group format."""
    results: List[ValidationResult] = []
    label = "iRiXhVV Format"

    if len(group) != 5:
        results.append(make_result(
            DOMAIN, label, group, "5 characters (iRiXhVV)",
            f"{len(group)} chars", ValidationStatus.ERROR,
            f"iRiXhVV group '{group}' must be 5 characters.",
        ))
        return results

    ir, ix, h, vv = group[0], group[1], group[2], group[3:5]

    if ir not in VALID_IR_CODES and ir != "/":
        results.append(make_result(
            DOMAIN, "iR Code", ir, "0–4 or /", ir,
            ValidationStatus.ERROR,
            f"Precipitation indicator iR='{ir}' is invalid (expected 0–4).",
            "Use 1 (precip in Sec1), 3 (no precip), or 4 (automatic)."
        ))

    if ix not in VALID_IX_CODES and ix != "/":
        results.append(make_result(
            DOMAIN, "iX Code", ix, "1–7 or /", ix,
            ValidationStatus.ERROR,
            f"Station/weather type indicator iX='{ix}' is invalid (expected 1–7).",
        ))

    if h not in VALID_H_CODES:
        results.append(make_result(
            DOMAIN, "h Code", h, "0–9 or /", h,
            ValidationStatus.ERROR,
            f"Cloud base height code h='{h}' is invalid (expected 0–9 or /).",
        ))

    # VV: two digits or '//'
    if vv != "//" and not vv.isdigit():
        results.append(make_result(
            DOMAIN, "VV Code", vv, "00–99 or //", vv,
            ValidationStatus.ERROR,
            f"Visibility code VV='{vv}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, label, group, "Valid iRiXhVV pattern",
            group, ValidationStatus.PASS,
            f"iRiXhVV group '{group}' has valid format."
        ))

    return results


def _validate_nddff(group: str) -> List[ValidationResult]:
    """Validate Nddff group format."""
    results: List[ValidationResult] = []
    label = "Nddff Format"

    if len(group) != 5:
        results.append(make_result(
            DOMAIN, label, group, "5 characters (Nddff)",
            f"{len(group)} chars", ValidationStatus.ERROR,
            f"Nddff group '{group}' must be 5 characters.",
        ))
        return results

    n, dd, ff = group[0], group[1:3], group[3:5]

    if n not in VALID_N_CODES:
        results.append(make_result(
            DOMAIN, "N Code", n, "0–9 or /", n,
            ValidationStatus.ERROR,
            f"Total cloud cover N='{n}' is invalid.",
        ))

    if dd != "//" and not dd.isdigit():
        results.append(make_result(
            DOMAIN, "dd Code", dd, "00–36, 99, or //", dd,
            ValidationStatus.ERROR,
            f"Wind direction dd='{dd}' is not numeric.",
        ))

    if ff != "//" and not ff.isdigit():
        results.append(make_result(
            DOMAIN, "ff Code", ff, "00–99 or //", ff,
            ValidationStatus.ERROR,
            f"Wind speed ff='{ff}' is not numeric.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, label, group, "Valid Nddff pattern",
            group, ValidationStatus.PASS,
            f"Nddff group '{group}' has valid format."
        ))

    return results


def _validate_1snttt(group: str) -> List[ValidationResult]:
    """Validate 1snTTT (air temperature) group format."""
    results: List[ValidationResult] = []

    sn = group[1]
    ttt = group[2:5]

    if sn not in ("0", "1", "/"):
        results.append(make_result(
            DOMAIN, "1snTTT Sign", sn, "0 (positive) or 1 (negative) or /",
            sn, ValidationStatus.ERROR,
            f"Temperature sign sn='{sn}' is invalid.",
        ))

    if ttt != "///" and not ttt.isdigit():
        results.append(make_result(
            DOMAIN, "1snTTT Value", ttt, "3 digits or ///",
            ttt, ValidationStatus.ERROR,
            f"Temperature value TTT='{ttt}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, "1snTTT Format", group, "1 + sign + 3 digits",
            group, ValidationStatus.PASS,
            f"Temperature group '{group}' has valid format."
        ))

    return results


def _validate_2snttt(group: str) -> List[ValidationResult]:
    """Validate 2snTdTdTd (dew point) group format."""
    results: List[ValidationResult] = []

    sn = group[1]
    ttt = group[2:5]

    if sn not in ("0", "1", "9", "/"):
        # sn=9 is used for RH reporting instead of dew point in some practices
        results.append(make_result(
            DOMAIN, "2snTdTdTd Sign", sn, "0, 1, 9, or /",
            sn, ValidationStatus.ERROR,
            f"Dew point sign sn='{sn}' is invalid.",
        ))

    if ttt != "///" and not ttt.isdigit():
        results.append(make_result(
            DOMAIN, "2snTdTdTd Value", ttt, "3 digits or ///",
            ttt, ValidationStatus.ERROR,
            f"Dew point value TdTdTd='{ttt}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, "2snTdTdTd Format", group, "2 + sign + 3 digits",
            group, ValidationStatus.PASS,
            f"Dew point group '{group}' has valid format."
        ))

    return results


def _validate_3pppp(group: str) -> List[ValidationResult]:
    """Validate 3P0P0P0P0 (station pressure) group format."""
    results: List[ValidationResult] = []
    val = group[1:5]

    if val != "////" and not val.isdigit():
        results.append(make_result(
            DOMAIN, "3P0P0P0P0 Value", val, "4 digits or ////",
            val, ValidationStatus.ERROR,
            f"Station pressure value '{val}' is invalid.",
        ))
    else:
        results.append(make_result(
            DOMAIN, "3P0P0P0P0 Format", group, "3 + 4 digits",
            group, ValidationStatus.PASS,
            f"Station pressure group '{group}' has valid format."
        ))

    return results


def _validate_4pppp(group: str) -> List[ValidationResult]:
    """Validate 4PPPP (MSL pressure) group format."""
    results: List[ValidationResult] = []
    val = group[1:5]

    if val != "////" and not val.isdigit():
        results.append(make_result(
            DOMAIN, "4PPPP Value", val, "4 digits or ////",
            val, ValidationStatus.ERROR,
            f"MSL pressure value '{val}' is invalid.",
        ))
    else:
        results.append(make_result(
            DOMAIN, "4PPPP Format", group, "4 + 4 digits",
            group, ValidationStatus.PASS,
            f"MSL pressure group '{group}' has valid format."
        ))

    return results


def _validate_5appp(group: str) -> List[ValidationResult]:
    """Validate 5appp (pressure tendency) group format."""
    results: List[ValidationResult] = []

    a = group[1]
    ppp = group[2:5]

    if a not in VALID_A_CODES and a != "/":
        results.append(make_result(
            DOMAIN, "5a Tendency Code", a, "0–8 or /",
            a, ValidationStatus.ERROR,
            f"Pressure tendency code a='{a}' is invalid.",
        ))

    if ppp != "///" and not ppp.isdigit():
        results.append(make_result(
            DOMAIN, "5ppp Value", ppp, "3 digits or ///",
            ppp, ValidationStatus.ERROR,
            f"Pressure change ppp='{ppp}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, "5appp Format", group, "5 + tendency + 3 digits",
            group, ValidationStatus.PASS,
            f"Pressure tendency group '{group}' has valid format."
        ))

    return results


def _validate_6rrrt(group: str) -> List[ValidationResult]:
    """Validate 6RRRtR (precipitation) group format."""
    results: List[ValidationResult] = []

    rrr = group[1:4]
    tr = group[4]

    if rrr != "///" and not rrr.isdigit():
        results.append(make_result(
            DOMAIN, "6RRR Value", rrr, "3 digits or ///",
            rrr, ValidationStatus.ERROR,
            f"Precipitation amount RRR='{rrr}' is invalid.",
        ))

    if tr not in VALID_TR_CODES and tr != "/":
        results.append(make_result(
            DOMAIN, "6tR Code", tr, "1–9 or /",
            tr, ValidationStatus.ERROR,
            f"Precipitation duration code tR='{tr}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, "6RRRtR Format", group, "6 + 3 digits + duration code",
            group, ValidationStatus.PASS,
            f"Precipitation group '{group}' has valid format."
        ))

    return results


def _validate_7www(group: str) -> List[ValidationResult]:
    """Validate 7wwW1W2 (weather) group format."""
    results: List[ValidationResult] = []

    ww = group[1:3]
    w1 = group[3]
    w2 = group[4]

    if ww != "//" and not ww.isdigit():
        results.append(make_result(
            DOMAIN, "7ww Code", ww, "00–99 or //",
            ww, ValidationStatus.ERROR,
            f"Present weather code ww='{ww}' is invalid.",
        ))

    if w1 not in VALID_W_CODES:
        results.append(make_result(
            DOMAIN, "7W1 Code", w1, "0–9 or /",
            w1, ValidationStatus.ERROR,
            f"Past weather W1='{w1}' is invalid.",
        ))

    if w2 not in VALID_W_CODES:
        results.append(make_result(
            DOMAIN, "7W2 Code", w2, "0–9 or /",
            w2, ValidationStatus.ERROR,
            f"Past weather W2='{w2}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, "7wwW1W2 Format", group, "7 + ww + W1 + W2",
            group, ValidationStatus.PASS,
            f"Weather group '{group}' has valid format."
        ))

    return results


def _validate_8cloud(group: str) -> List[ValidationResult]:
    """Validate 8NhCLCMCH (cloud detail) group format."""
    results: List[ValidationResult] = []

    nh = group[1]
    cl = group[2]
    cm = group[3]
    ch = group[4]

    if nh not in VALID_NH_CODES:
        results.append(make_result(
            DOMAIN, "8Nh Code", nh, "0–9 or /", nh,
            ValidationStatus.ERROR,
            f"Low cloud amount Nh='{nh}' is invalid.",
        ))

    if cl not in VALID_CL_CODES:
        results.append(make_result(
            DOMAIN, "8CL Code", cl, "0–9 or /", cl,
            ValidationStatus.ERROR,
            f"Low cloud type CL='{cl}' is invalid.",
        ))

    if cm not in VALID_CM_CODES:
        results.append(make_result(
            DOMAIN, "8CM Code", cm, "0–9 or /", cm,
            ValidationStatus.ERROR,
            f"Middle cloud type CM='{cm}' is invalid.",
        ))

    if ch not in VALID_CH_CODES:
        results.append(make_result(
            DOMAIN, "8CH Code", ch, "0–9 or /", ch,
            ValidationStatus.ERROR,
            f"High cloud type CH='{ch}' is invalid.",
        ))

    if not results:
        results.append(make_result(
            DOMAIN, "8NhCLCMCH Format", group, "8 + Nh + CL + CM + CH",
            group, ValidationStatus.PASS,
            f"Cloud detail group '{group}' has valid format."
        ))

    return results


def _validate_9gust(group: str) -> List[ValidationResult]:
    """Validate 9-prefixed group (wind gust 00fff) in Section 1."""
    results: List[ValidationResult] = []
    # 00fff format for gusts > 99 units
    if group[1:3] == "00" and group[3:5].isdigit():
        results.append(make_result(
            DOMAIN, "Gust Group Format", group, "900ff",
            group, ValidationStatus.PASS,
            f"Wind gust group '{group}' has valid format."
        ))
    else:
        results.append(make_result(
            DOMAIN, "Section 1 Group-9", group, "Expected 900ff gust format",
            group, ValidationStatus.WARNING,
            f"Unrecognized group '{group}' starting with 9 in Section 1.",
        ))
    return results


# -----------------------------------------------------------------------
# Section 333 / 555 lightweight format checks
# -----------------------------------------------------------------------

def _validate_sec333_group(group: str) -> List[ValidationResult]:
    """Lightweight format validation for Section 333 groups."""
    results: List[ValidationResult] = []

    if len(group) < 4:
        results.append(make_result(
            DOMAIN, "Section 333 Group", group, "≥ 4 characters",
            f"{len(group)} chars", ValidationStatus.WARNING,
            f"Section 333 group '{group}' is unusually short.",
        ))
        return results

    prefix = group[0]
    # Most Section 333 groups follow the same snTTT pattern or specific formats
    # We check that non-/ characters are digits
    value_part = group[1:]
    non_slash = value_part.replace("/", "")
    if non_slash and not non_slash.isdigit():
        results.append(make_result(
            DOMAIN, "Section 333 Group Content", group,
            "Digits and '/' characters only",
            group, ValidationStatus.WARNING,
            f"Section 333 group '{group}' contains unexpected characters.",
        ))
    else:
        results.append(make_result(
            DOMAIN, "Section 333 Group Format", group,
            "Valid numeric/slash content",
            group, ValidationStatus.PASS,
            f"Section 333 group '{group}' has valid format."
        ))

    return results


def _validate_sec555_group(group: str) -> List[ValidationResult]:
    """Lightweight format validation for Section 555 (national) groups."""
    results: List[ValidationResult] = []

    if len(group) < 4:
        results.append(make_result(
            DOMAIN, "Section 555 Group", group, "≥ 4 characters",
            f"{len(group)} chars", ValidationStatus.WARNING,
            f"Section 555 group '{group}' is unusually short.",
        ))
        return results

    value_part = group[1:]
    non_slash = value_part.replace("/", "")
    if non_slash and not non_slash.isdigit():
        results.append(make_result(
            DOMAIN, "Section 555 Group Content", group,
            "Digits and '/' characters only",
            group, ValidationStatus.WARNING,
            f"Section 555 group '{group}' contains unexpected characters.",
        ))
    else:
        results.append(make_result(
            DOMAIN, "Section 555 Group Format", group,
            "Valid numeric/slash content",
            group, ValidationStatus.PASS,
            f"Section 555 group '{group}' has valid format."
        ))

    return results


# -----------------------------------------------------------------------
# Tokenizer
# -----------------------------------------------------------------------

def _tokenize(synop_string: str) -> List[str]:
    cleaned = synop_string.replace("\n", " ").replace("\r", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.split() if cleaned else []
