"""Temporal ordering and causality validator."""

from typing import Any

from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.report import ValidationDiagnostic, ValidationOutcome
from spindle.core.state_service import StoryState
from spindle.models.base import ConstraintSeverity


class ChronologyValidator(BaseConstraintValidator):
    """Validates that causal prerequisites strictly precede the proposed event."""

    validator_id = "DETERMINISTIC_CHRONOLOGY"
    name = "Chronology and Causality Validator"

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        diagnostics: list[ValidationDiagnostic] = []

        # Target narrative position of the proposed event/scene
        target_pos = float(proposal.get("narrative_position", story_state.narrative_position))
        target_chrono = proposal.get("chronological_order")
        if target_chrono is not None:
            target_chrono = float(target_chrono)

        # Preconditions or causal dependencies
        dependencies = proposal.get("causal_dependencies") or proposal.get("preconditions") or []

        for dep in dependencies:
            dep_event = story_state.get_event(dep)

            if not dep_event:
                diagnostics.append(
                    ValidationDiagnostic(
                        rule_id=f"{self.validator_id}_MISSING_DEPENDENCY",
                        rule_name="Unresolved Causal Precondition",
                        outcome=ValidationOutcome.FAIL,
                        severity=ConstraintSeverity.HARD,
                        message=(
                            f"Proposed event requires causal prerequisite '{dep}', but it has not "
                            f"been established in canon up to narrative position {target_pos}."
                        ),
                        evidence=[f"Missing prerequisite: {dep}"],
                        remediation_hint=(
                            f"Ensure '{dep}' is introduced in an earlier scene or remove dependency."
                        ),
                    )
                )
                continue

            # Check manuscript narrative position
            if dep_event.narrative_position > target_pos:
                diagnostics.append(
                    ValidationDiagnostic(
                        rule_id=f"{self.validator_id}_NARRATIVE_ORDER_VIOLATION",
                        rule_name="Narrative Sequence Causality Inversion",
                        outcome=ValidationOutcome.FAIL,
                        severity=ConstraintSeverity.HARD,
                        message=(
                            f"Prerequisite event '{dep_event.title}' occurs at narrative position "
                            f"{dep_event.narrative_position}, which is after proposed position {target_pos}."
                        ),
                        evidence=[
                            f"Prerequisite narrative position: {dep_event.narrative_position}",
                            f"Proposed narrative position: {target_pos}",
                        ],
                        remediation_hint=(
                            f"Move proposed event after narrative position {dep_event.narrative_position} "
                            f"or establish '{dep_event.title}' earlier in the manuscript."
                        ),
                    )
                )

            # Check chronological ordering if both have timestamps
            if target_chrono is not None and dep_event.chronological_order is not None:
                if dep_event.chronological_order > target_chrono:
                    diagnostics.append(
                        ValidationDiagnostic(
                            rule_id=f"{self.validator_id}_CHRONOLOGY_PARADOX",
                            rule_name="Temporal Causality Paradox",
                            outcome=ValidationOutcome.FAIL,
                            severity=ConstraintSeverity.HARD,
                            message=(
                                f"Causality paradox: Prerequisite '{dep_event.title}' occurs at "
                                f"chronological time {dep_event.chronological_order}, which is later "
                                f"in world history than proposed event's chronological time {target_chrono}."
                            ),
                            evidence=[
                                f"Prerequisite chronological order: {dep_event.chronological_order}",
                                f"Proposed chronological order: {target_chrono}",
                            ],
                            remediation_hint=(
                                "Adjust story chronology so causes precede their effects in timeline."
                            ),
                        )
                    )

        if not diagnostics:
            diagnostics.append(
                ValidationDiagnostic(
                    rule_id=f"{self.validator_id}_PASS",
                    rule_name="Chronological Consistency",
                    outcome=ValidationOutcome.PASS,
                    severity=ConstraintSeverity.HARD,
                    message="All causal dependencies and chronological sequences are valid.",
                )
            )

        return diagnostics
