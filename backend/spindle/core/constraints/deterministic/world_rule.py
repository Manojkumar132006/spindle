"""Hard world rule limit validator."""

from typing import Any

from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.report import ValidationDiagnostic, ValidationOutcome
from spindle.core.state_service import StoryState
from spindle.models.base import ConstraintSeverity, EnforcementLevel, RuleType


class WorldRuleValidator(BaseConstraintValidator):
    """Validates that proposed actions adhere to explicit physical, magical, and societal world rules."""

    validator_id = "DETERMINISTIC_WORLD_RULE"
    name = "World Rule Limit Validator"

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        diagnostics: list[ValidationDiagnostic] = []

        proposed_actions = [str(a).lower() for a in proposal.get("actions", [])]
        premise_text = str(proposal.get("premise", "")).lower()
        title_text = str(proposal.get("title", "")).lower()
        combined_text = f"{title_text} {premise_text} {' '.join(proposed_actions)}"

        for rule in story_state.active_world_rules:
            is_hard = rule.enforcement_level == EnforcementLevel.HARD.value
            rule_desc_lower = rule.description.lower()
            meta = rule.metadata_json or {}

            # 1. Check explicit forbidden triggers in metadata
            forbidden_triggers = [str(t).lower() for t in meta.get("forbidden_triggers", [])]
            for trigger in forbidden_triggers:
                if trigger in combined_text:
                    severity = ConstraintSeverity.HARD if is_hard else ConstraintSeverity.SOFT
                    outcome = ValidationOutcome.FAIL if is_hard else ValidationOutcome.WARNING

                    diagnostics.append(
                        ValidationDiagnostic(
                            rule_id=f"{self.validator_id}_{rule.name.upper().replace(' ', '_')}",
                            rule_name=f"World Rule Breach: {rule.name}",
                            outcome=outcome,
                            severity=severity,
                            message=(
                                f"Proposed development triggers forbidden condition '{trigger}' "
                                f"defined by {rule.rule_type} rule '{rule.name}'."
                            ),
                            evidence=[
                                f"Rule Name: {rule.name}",
                                f"Rule Description: {rule.description}",
                                f"Trigger Detected: {trigger}",
                            ],
                            remediation_hint=f"Modify action to comply with {rule.name}: '{rule.description}'.",
                        )
                    )

            # 2. Check magic resurrection prohibition rule pattern
            if rule.rule_type == RuleType.MAGIC.value and any(
                word in rule_desc_lower
                for word in ("resurrection is impossible", "cannot revive", "no return from death")
            ):
                if any(
                    word in combined_text
                    for word in (
                        "resurrect",
                        "revive",
                        "bring back to life",
                        "brought back to life",
                    )
                ):
                    diagnostics.append(
                        ValidationDiagnostic(
                            rule_id=f"{self.validator_id}_RESURRECTION_BREACH",
                            rule_name="Absolute Magic Law: No Resurrection",
                            outcome=ValidationOutcome.FAIL,
                            severity=ConstraintSeverity.HARD,
                            message=(
                                f"Proposed development involves reviving or resurrecting a character, "
                                f"violating absolute world rule '{rule.name}'."
                            ),
                            evidence=[
                                f"Rule: {rule.name} - {rule.description}",
                                "Proposal mentions resurrection/revival.",
                            ],
                            remediation_hint="Canon strictly prohibits resurrecting the dead. Explore non-revival plot avenues.",
                        )
                    )

        # Also evaluate explicit active constraints from the database
        for constraint in story_state.active_constraints:
            meta = constraint.parameters or {}
            prohibited_actions = [str(a).lower() for a in meta.get("prohibited_actions", [])]
            for prohibited in prohibited_actions:
                if prohibited in combined_text:
                    sev = constraint.severity or ConstraintSeverity.HARD.value
                    is_hard = sev in (ConstraintSeverity.HARD.value, ConstraintSeverity.HARD)
                    outcome = ValidationOutcome.FAIL if is_hard else ValidationOutcome.WARNING
                    severity = ConstraintSeverity.HARD if is_hard else ConstraintSeverity.SOFT

                    diagnostics.append(
                        ValidationDiagnostic(
                            rule_id=f"CONSTRAINT_{constraint.name.upper().replace(' ', '_')}",
                            rule_name=f"Author Constraint: {constraint.name}",
                            outcome=outcome,
                            severity=severity,
                            message=(
                                f"Proposed content contains prohibited element '{prohibited}' "
                                f"governed by constraint '{constraint.name}'."
                            ),
                            evidence=[
                                f"Constraint: {constraint.name}",
                                f"Description: {constraint.description}",
                            ],
                            remediation_hint="Revise proposal to adhere to author constraint boundaries.",
                        )
                    )

        if not diagnostics:
            diagnostics.append(
                ValidationDiagnostic(
                    rule_id=f"{self.validator_id}_PASS",
                    rule_name="World Rule Compliance",
                    outcome=ValidationOutcome.PASS,
                    severity=ConstraintSeverity.HARD,
                    message="All actions comply with active world rules and author constraints.",
                )
            )

        return diagnostics
