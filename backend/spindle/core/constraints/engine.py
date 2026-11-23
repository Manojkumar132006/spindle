"""Centralized Constraint Engine orchestrating narrative validators."""

from typing import Any

from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.deterministic.chronology import ChronologyValidator
from spindle.core.constraints.deterministic.epistemic import EpistemicValidator
from spindle.core.constraints.deterministic.life_status import LifeStatusValidator
from spindle.core.constraints.deterministic.world_rule import WorldRuleValidator
from spindle.core.constraints.report import (
    ValidationDiagnostic,
    ValidationOutcome,
    ValidationReport,
)
from spindle.core.state_service import StoryState
from spindle.models.base import ConstraintSeverity


class ConstraintEngine:
    """Evaluates narrative proposals against point-in-time story state using deterministic & semantic rules."""

    def __init__(self, validators: list[BaseConstraintValidator] | None = None) -> None:
        if validators is not None:
            self.validators = validators
        else:
            # Register standard deterministic validators
            self.validators = [
                ChronologyValidator(),
                LifeStatusValidator(),
                EpistemicValidator(),
                WorldRuleValidator(),
            ]

    def register_validator(self, validator: BaseConstraintValidator) -> None:
        """Register an additional custom or semantic validator."""
        self.validators.append(validator)

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> ValidationReport:
        """Execute all registered validators and produce a consolidated ValidationReport."""
        all_diagnostics: list[ValidationDiagnostic] = []

        for validator in self.validators:
            diag_results = await validator.validate(proposal, story_state)
            all_diagnostics.extend(diag_results)

        # Check for hard failures, soft warnings, etc.
        has_hard_fail = any(
            d.outcome == ValidationOutcome.FAIL and d.severity == ConstraintSeverity.HARD
            for d in all_diagnostics
        )
        has_soft_fail = any(
            d.outcome == ValidationOutcome.FAIL and d.severity != ConstraintSeverity.HARD
            for d in all_diagnostics
        )
        has_warning = any(d.outcome == ValidationOutcome.WARNING for d in all_diagnostics)
        has_insufficient_context = any(
            d.outcome == ValidationOutcome.INSUFFICIENT_CONTEXT for d in all_diagnostics
        )

        if has_hard_fail:
            overall = ValidationOutcome.FAIL
            summary = (
                "Validation FAILED: Detected hard constraint violations blocking canon compatibility. "
                "Requires revision before author approval."
            )
        elif has_soft_fail or has_warning:
            overall = ValidationOutcome.WARNING
            summary = (
                "Validation PASSED with WARNINGS: Soft constraints or behavioral tensions identified. "
                "Review diagnostics before committing to canon."
            )
        elif has_insufficient_context:
            overall = ValidationOutcome.INSUFFICIENT_CONTEXT
            summary = (
                "Validation INSUFFICIENT_CONTEXT: Missing narrative context required to establish "
                "canon consistency."
            )
        else:
            overall = ValidationOutcome.PASS
            summary = "Validation PASSED: Proposal satisfies all active narrative constraints."

        return ValidationReport(
            overall_outcome=overall,
            diagnostics=all_diagnostics,
            summary=summary,
        )


# Default singleton instance
default_constraint_engine = ConstraintEngine()
