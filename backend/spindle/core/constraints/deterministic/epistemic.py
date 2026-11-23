"""Character epistemic boundary validator."""

from typing import Any

from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.report import ValidationDiagnostic, ValidationOutcome
from spindle.core.state_service import StoryState
from spindle.models.base import ConstraintSeverity, KnowledgeStatus


class EpistemicValidator(BaseConstraintValidator):
    """Validates that characters do not act on facts or secrets they have not learned."""

    validator_id = "DETERMINISTIC_EPISTEMIC"
    name = "Epistemic Boundary Validator"

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        diagnostics: list[ValidationDiagnostic] = []
        target_pos = float(proposal.get("narrative_position", story_state.narrative_position))

        # Check explicit knowledge requirements in proposal
        knowledge_actions = (
            proposal.get("required_knowledge") or proposal.get("epistemic_actions") or []
        )

        for item in knowledge_actions:
            char_ident = item.get("character") or item.get("character_id")
            fact_id = item.get("fact") or item.get("fact_id") or item.get("secret")

            if not char_ident or not fact_id:
                continue

            char = story_state.get_character(char_ident)
            if not char:
                continue

            # Query knowledge items held at or prior to target_pos
            known_items = story_state.get_character_knowledge(char.id, fact_id)

            if not known_items:
                # Completely unknown
                diagnostics.append(
                    ValidationDiagnostic(
                        rule_id=f"{self.validator_id}_ANACHRONISTIC_LEAKAGE",
                        rule_name="Unearned Epistemic Access",
                        outcome=ValidationOutcome.FAIL,
                        severity=ConstraintSeverity.HARD,
                        message=(
                            f"Character '{char.name}' attempts to act upon secret or fact '{fact_id}' "
                            f"without having acquired it by narrative position {target_pos}."
                        ),
                        evidence=[
                            f"Character: {char.name}",
                            f"Fact/Secret: {fact_id}",
                            f"Knowledge status at {target_pos}: UNKNOWN",
                        ],
                        remediation_hint=(
                            f"Stage a scene where '{char.name}' learns '{fact_id}' prior to {target_pos}, "
                            f"or prevent them from acting on this secret."
                        ),
                    )
                )
            else:
                latest = known_items[-1]
                status_val = latest.knowledge_status

                # Check if character only suspects or has a false belief
                if status_val == KnowledgeStatus.FALSE_BELIEF.value:
                    diagnostics.append(
                        ValidationDiagnostic(
                            rule_id=f"{self.validator_id}_FALSE_BELIEF_TENSION",
                            rule_name="False Belief Epistemic Tension",
                            outcome=ValidationOutcome.WARNING,
                            severity=ConstraintSeverity.WARNING,
                            message=(
                                f"Character '{char.name}' holds a FALSE_BELIEF regarding '{fact_id}'. "
                                f"Ensure their actions reflect this misunderstanding rather than truth."
                            ),
                            evidence=[
                                f"Character: {char.name}",
                                f"Status: {status_val}",
                                f"Details: {latest.details or 'N/A'}",
                            ],
                            remediation_hint="Align character behavior with their mistaken perception.",
                        )
                    )
                elif status_val == KnowledgeStatus.SUSPECTED.value:
                    diagnostics.append(
                        ValidationDiagnostic(
                            rule_id=f"{self.validator_id}_SUSPECTED_KNOWLEDGE_WARNING",
                            rule_name="Unconfirmed Knowledge Reliance",
                            outcome=ValidationOutcome.WARNING,
                            severity=ConstraintSeverity.WARNING,
                            message=(
                                f"Character '{char.name}' only SUSPECTS '{fact_id}'. Acting with absolute "
                                f"certainty may weaken narrative credibility."
                            ),
                            evidence=[
                                f"Character: {char.name}",
                                f"Status: {status_val}",
                            ],
                            remediation_hint="Show character acting tentatively or investigating further.",
                        )
                    )

        if not diagnostics:
            diagnostics.append(
                ValidationDiagnostic(
                    rule_id=f"{self.validator_id}_PASS",
                    rule_name="Epistemic Boundary Integrity",
                    outcome=ValidationOutcome.PASS,
                    severity=ConstraintSeverity.HARD,
                    message="All character knowledge dependencies are earned and canon-compliant.",
                )
            )

        return diagnostics
