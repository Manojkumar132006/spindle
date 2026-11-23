"""Character life and death availability validator."""

from typing import Any

from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.report import ValidationDiagnostic, ValidationOutcome
from spindle.core.state_service import StoryState
from spindle.models.base import ConstraintSeverity


class LifeStatusValidator(BaseConstraintValidator):
    """Validates that deceased characters do not actively participate in scenes."""

    validator_id = "DETERMINISTIC_LIFE_STATUS"
    name = "Character Life Status Validator"

    ALLOWED_EXCEPTIONS = {
        "flashback",
        "dream",
        "vision",
        "hallucination",
        "ghost",
        "memory",
        "corpse",
        "memorial",
    }

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        diagnostics: list[ValidationDiagnostic] = []

        # Check if scene context permits deceased character presence
        scene_type = str(proposal.get("scene_type", "")).lower()
        is_flashback = bool(proposal.get("is_flashback", False))
        metadata = proposal.get("metadata", {}) or {}
        tags = set(str(t).lower() for t in proposal.get("tags", []))

        is_exempt = (
            is_flashback
            or scene_type in self.ALLOWED_EXCEPTIONS
            or any(exc in tags for exc in self.ALLOWED_EXCEPTIONS)
            or metadata.get("is_flashback", False)
        )

        participants = proposal.get("participants") or proposal.get("involved_characters") or []

        for p in participants:
            char = story_state.get_character(p)
            if not char:
                continue

            is_alive = story_state.is_character_alive(char.id)
            if not is_alive and not is_exempt:
                diagnostics.append(
                    ValidationDiagnostic(
                        rule_id=f"{self.validator_id}_DECEASED_PARTICIPATION",
                        rule_name="Deceased Character Physical Availability",
                        outcome=ValidationOutcome.FAIL,
                        severity=ConstraintSeverity.HARD,
                        message=(
                            f"Character '{char.name}' is recorded as deceased at narrative position "
                            f"{story_state.narrative_position} and cannot actively participate in scene."
                        ),
                        evidence=[
                            f"Character: {char.name} ({char.id})",
                            f"Current state: {char.current_state}",
                            f"Scene type: {scene_type or 'standard'}",
                        ],
                        remediation_hint=(
                            f"Remove '{char.name}' from active participants, or explicitly mark the scene "
                            f"as a flashback, vision, or memory."
                        ),
                    )
                )

        if not diagnostics:
            diagnostics.append(
                ValidationDiagnostic(
                    rule_id=f"{self.validator_id}_PASS",
                    rule_name="Life Status Consistency",
                    outcome=ValidationOutcome.PASS,
                    severity=ConstraintSeverity.HARD,
                    message="All participating characters are alive or validly contextualized.",
                )
            )

        return diagnostics
