"""Unit tests for suggestion lifecycle state machine and transition guards."""

import pytest

from spindle.core.lifecycle import (
    InvalidLifecycleTransitionError,
    validate_lifecycle_transition,
)
from spindle.models.base import ApprovalStatus


def test_valid_lifecycle_transitions():
    """Verify that expected legal lifecycle paths pass validation."""
    # Standard author review path
    validate_lifecycle_transition(ApprovalStatus.GENERATED, ApprovalStatus.VALIDATING)
    validate_lifecycle_transition(ApprovalStatus.VALIDATING, ApprovalStatus.VALIDATED)
    validate_lifecycle_transition(ApprovalStatus.VALIDATED, ApprovalStatus.PENDING_AUTHOR_APPROVAL)
    validate_lifecycle_transition(ApprovalStatus.PENDING_AUTHOR_APPROVAL, ApprovalStatus.APPROVED)
    validate_lifecycle_transition(ApprovalStatus.APPROVED, ApprovalStatus.COMMITTED)

    # Author edit path
    validate_lifecycle_transition(ApprovalStatus.PENDING_AUTHOR_APPROVAL, ApprovalStatus.EDITED)
    validate_lifecycle_transition(ApprovalStatus.EDITED, ApprovalStatus.COMMITTED)

    # Self-transition is a no-op
    validate_lifecycle_transition(ApprovalStatus.APPROVED, ApprovalStatus.APPROVED)


def test_illegal_lifecycle_transitions_guard():
    """Verify that illegal transitions raise InvalidLifecycleTransitionError."""
    # Cannot jump directly from GENERATED to COMMITTED without review
    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(ApprovalStatus.GENERATED, ApprovalStatus.COMMITTED)

    # Cannot commit a REJECTED suggestion
    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(ApprovalStatus.REJECTED, ApprovalStatus.COMMITTED)

    # Cannot approve a REJECTED suggestion without fresh revision
    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(ApprovalStatus.REJECTED, ApprovalStatus.APPROVED)

    # Cannot edit or reject an already COMMITTED canon document
    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(ApprovalStatus.COMMITTED, ApprovalStatus.EDITED)

    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(ApprovalStatus.COMMITTED, ApprovalStatus.REJECTED)
