"""Character existence and hallucination prevention constraint validator."""

import re
from typing import Any

from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.report import ValidationDiagnostic, ValidationOutcome
from spindle.core.state_service import StoryState
from spindle.models.base import ConstraintSeverity


class EntityExistenceValidator(BaseConstraintValidator):
    """Validates that characters involved in narrative proposals actually exist in the author's story."""

    validator_id = "DETERMINISTIC_ENTITY_EXISTENCE"
    name = "Entity Existence & Hallucination Validator"

    # Generic incidental role nouns that do not represent specific named characters
    ALLOWED_GENERIC_ROLES = {
        "guard",
        "guards",
        "sentry",
        "sentries",
        "conductor",
        "train conductor",
        "station attendant",
        "attendant",
        "attendants",
        "driver",
        "passengers",
        "passenger",
        "crowd",
        "bystander",
        "bystanders",
        "doctor",
        "officer",
        "police",
        "soldier",
        "soldiers",
        "merchant",
        "merchants",
        "courier",
        "archivist",
        "clerk",
        "innkeeper",
        "bartender",
        "villager",
        "villagers",
        "unnamed",
        "extra",
        "extras",
        "stranger",
        "strangers",
    }

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        diagnostics: list[ValidationDiagnostic] = []

        # If author has not established any characters yet, do not block creation
        if not story_state.characters:
            return diagnostics

        established_names: set[str] = set()
        for char in story_state.characters:
            established_names.add(char.name.strip().lower())
            for alias in char.aliases or []:
                if isinstance(alias, str) and alias.strip():
                    established_names.add(alias.strip().lower())

        participants = (
            proposal.get("involved_characters")
            or proposal.get("participants")
            or []
        )

        for p in participants:
            clean_name = re.sub(r"[\[\]]", "", str(p)).strip()
            if not clean_name:
                continue

            lower_name = clean_name.lower()

            # 1. Exact or partial match with established character name or alias
            if lower_name in established_names:
                continue

            # Check if any established name is a substring or word inside
            if any(lower_name in est or est in lower_name for est in established_names):
                continue

            # 2. Check if it's an allowed generic extra / role title
            if lower_name in self.ALLOWED_GENERIC_ROLES or any(
                role in lower_name for role in self.ALLOWED_GENERIC_ROLES
            ):
                continue

            # 3. Otherwise, it is an unestablished / hallucinated character
            diagnostics.append(
                ValidationDiagnostic(
                    rule_id=f"{self.validator_id}_UNKNOWN_CHARACTER",
                    rule_name="Unestablished Character Hallucination",
                    outcome=ValidationOutcome.FAIL,
                    severity=ConstraintSeverity.HARD,
                    message=(
                        f"Character '{clean_name}' does not exist in the author's established story cast. "
                        f"Available characters are: {', '.join(c.name for c in story_state.characters)}. "
                        "Do not invent new character names. Use only established cast or generic role titles."
                    ),
                    evidence=[f"Proposing entity: {clean_name}"],
                    remediation_hint=(
                        f"Replace '{clean_name}' with one of the established characters "
                        f"({', '.join(c.name for c in story_state.characters)}) or refer to them generically."
                    ),
                )
            )

        return diagnostics
