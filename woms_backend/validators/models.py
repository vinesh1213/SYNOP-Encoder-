# =============================================================================
# SYNOP Validation Engine — Data Models
# =============================================================================
# Defines the core data structures used throughout the validation pipeline:
#   - ValidationStatus  (PASS / WARNING / ERROR)
#   - ValidationResult  (individual check outcome)
#   - ValidationReport  (aggregated final report)
#
# These are plain dataclasses so the validators stay framework-agnostic.
# Pydantic mirrors live in models/schemas.py for FastAPI serialization.
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ValidationStatus(str, Enum):
    """Tri-state outcome for every individual validation check."""
    PASS = "PASS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ReportStatus(str, Enum):
    """Overall report verdict."""
    ACCEPTED = "ACCEPTED"
    WARNING = "WARNING"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Single validation check result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """
    Captures the outcome of a single validation check.

    Attributes
    ----------
    validation_name : str
        Human-readable name of the check, e.g. "Temperature Range Check".
    input_value : Any
        The raw value that was inspected.
    expected_range : str
        Textual description of the acceptable range or condition.
    actual_value : Any
        The resolved / decoded value used for the check.
    status : ValidationStatus
        PASS, WARNING, or ERROR.
    error_message : str
        Descriptive message suitable for meteorological observers.
    suggested_correction : str
        Guidance on how to fix the issue, or empty string if PASS.
    domain : str
        Validation domain this result belongs to (e.g. "temperature",
        "pressure"), used for grouping in the final report.
    """
    validation_name: str
    input_value: Any
    expected_range: str
    actual_value: Any
    status: ValidationStatus
    error_message: str
    suggested_correction: str = ""
    domain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_name": self.validation_name,
            "input_value": _safe_serialize(self.input_value),
            "expected_range": self.expected_range,
            "actual_value": _safe_serialize(self.actual_value),
            "status": self.status.value,
            "error_message": self.error_message,
            "suggested_correction": self.suggested_correction,
            "domain": self.domain,
        }


# ---------------------------------------------------------------------------
# Aggregated final validation report
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """
    The final, structured output of the validation engine.

    Contains counts, per-domain summaries, and the full list of individual
    results so the caller can render detailed feedback to the observer.
    """
    status: ReportStatus = ReportStatus.ACCEPTED
    overall_score: float = 100.0
    total_checks: int = 0
    passed: int = 0
    warnings: int = 0
    errors: int = 0
    validation_summary: Dict[str, str] = field(default_factory=dict)
    errors_list: List[Dict[str, Any]] = field(default_factory=list)
    warnings_list: List[Dict[str, Any]] = field(default_factory=list)
    all_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "overall_score": round(self.overall_score, 1),
            "total_checks": self.total_checks,
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
            "validation_summary": self.validation_summary,
            "errors_list": self.errors_list,
            "warnings_list": self.warnings_list,
            "all_results": self.all_results,
        }



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    domain: str,
    name: str,
    input_value: Any,
    expected: str,
    actual: Any,
    status: ValidationStatus,
    message: str,
    suggestion: str = "",
) -> ValidationResult:
    """Convenience factory that auto-fills the *domain* field."""
    return ValidationResult(
        validation_name=name,
        input_value=input_value,
        expected_range=expected,
        actual_value=actual,
        status=status,
        error_message=message,
        suggested_correction=suggestion,
        domain=domain,
    )


def _safe_serialize(value: Any) -> Any:
    """Ensure a value is JSON-serializable."""
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)
