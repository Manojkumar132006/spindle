"""Validation report models and outcomes for the Constraint Engine."""

import enum
from dataclasses import dataclass, field
from typing import Any

from spindle.models.base import ConstraintSeverity


class ValidationOutcome(enum.StrEnum):
    """Possible outcomes of a constraint validation check."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


@dataclass
class ValidationDiagnostic:
    """Detailed diagnostic result for an individual constraint or rule check."""

    rule_id: str
    rule_name: str
    outcome: ValidationOutcome
    severity: ConstraintSeverity = ConstraintSeverity.HARD
    message: str = ""
    evidence: list[str] = field(default_factory=list)
    remediation_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Comprehensive validation report compiled across all constraint checkers."""

    overall_outcome: ValidationOutcome
    diagnostics: list[ValidationDiagnostic] = field(default_factory=list)
    summary: str = ""

    @property
    def is_valid(self) -> bool:
        """Return True if the proposal is canon-compatible (PASS or WARNING only)."""
        return self.overall_outcome in (ValidationOutcome.PASS, ValidationOutcome.WARNING)

    @property
    def has_hard_failures(self) -> bool:
        """Check if any hard constraint failed."""
        return any(
            d.outcome == ValidationOutcome.FAIL and d.severity == ConstraintSeverity.HARD
            for d in self.diagnostics
        )

    @property
    def passed_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.outcome == ValidationOutcome.PASS)

    @property
    def failed_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.outcome == ValidationOutcome.FAIL)

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.outcome == ValidationOutcome.WARNING)

    @property
    def insufficient_context_count(self) -> int:
        return sum(
            1 for d in self.diagnostics if d.outcome == ValidationOutcome.INSUFFICIENT_CONTEXT
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary format for persistence and JSON APIs."""
        return {
            "overall_outcome": self.overall_outcome.value,
            "is_valid": self.is_valid,
            "has_hard_failures": self.has_hard_failures,
            "summary": self.summary,
            "counts": {
                "passed": self.passed_count,
                "failed": self.failed_count,
                "warnings": self.warning_count,
                "insufficient_context": self.insufficient_context_count,
            },
            "diagnostics": [
                {
                    "rule_id": d.rule_id,
                    "rule_name": d.rule_name,
                    "outcome": d.outcome.value,
                    "severity": d.severity.value,
                    "message": d.message,
                    "evidence": d.evidence,
                    "remediation_hint": d.remediation_hint,
                    "metadata": d.metadata,
                }
                for d in self.diagnostics
            ],
        }
