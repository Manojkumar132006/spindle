"""Suggestion lifecycle state machine and transition enforcement."""

from spindle.models.base import ApprovalStatus


class InvalidLifecycleTransitionError(ValueError):
    """Raised when an illegal lifecycle state transition is attempted."""

    def __init__(self, current_status: str, target_status: str, message: str | None = None):
        msg = (
            message or f"Cannot transition suggestion from '{current_status}' to '{target_status}'."
        )
        super().__init__(msg)
        self.current_status = current_status
        self.target_status = target_status


# Valid transition state graph for creative suggestions
VALID_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.GENERATED: {
        ApprovalStatus.VALIDATING,
        ApprovalStatus.REJECTED,
        ApprovalStatus.PENDING_AUTHOR_APPROVAL,  # Direct transition when validation is synchronized
    },
    ApprovalStatus.VALIDATING: {
        ApprovalStatus.VALIDATED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.PENDING_AUTHOR_APPROVAL,
    },
    ApprovalStatus.VALIDATED: {
        ApprovalStatus.PENDING_AUTHOR_APPROVAL,
        ApprovalStatus.REJECTED,
    },
    ApprovalStatus.PENDING_AUTHOR_APPROVAL: {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.EDITED,
    },
    ApprovalStatus.EDITED: {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.PENDING_AUTHOR_APPROVAL,
        ApprovalStatus.COMMITTED,  # Author can directly commit an edited suggestion
    },
    ApprovalStatus.APPROVED: {
        ApprovalStatus.COMMITTED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.EDITED,
    },
    ApprovalStatus.REJECTED: set(),  # Terminal state
    ApprovalStatus.COMMITTED: set(),  # Terminal state: canon is committed and immutable
}


def validate_lifecycle_transition(
    current_status: ApprovalStatus | str,
    target_status: ApprovalStatus | str,
) -> None:
    """Validate that the target state transition is permitted by the lifecycle state machine.

    Raises:
        InvalidLifecycleTransitionError: if transition violates author-approval or lifecycle rules.
    """
    curr = ApprovalStatus(current_status) if isinstance(current_status, str) else current_status
    target = ApprovalStatus(target_status) if isinstance(target_status, str) else target_status

    if curr == target:
        return

    allowed = VALID_TRANSITIONS.get(curr, set())
    if target not in allowed:
        raise InvalidLifecycleTransitionError(
            current_status=curr.value,
            target_status=target.value,
            message=(
                f"Illegal lifecycle transition: cannot move suggestion from '{curr.value}' "
                f"to '{target.value}'. Allowed transitions from '{curr.value}': "
                f"{[s.value for s in allowed]}."
            ),
        )
