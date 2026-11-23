"""Base class for constraint engine validators."""

from abc import ABC, abstractmethod
from typing import Any

from spindle.core.constraints.report import ValidationDiagnostic
from spindle.core.state_service import StoryState


class BaseConstraintValidator(ABC):
    """Abstract interface for all constraint checkers."""

    validator_id: str
    name: str

    @abstractmethod
    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        """Validate a proposed narrative development against the story state."""
        pass
