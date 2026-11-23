"""Unit tests for CanonCommitService non-destructive commit and provenance creation."""

import pytest
from sqlalchemy import select

from spindle.core.commit_service import CanonCommitService
from spindle.core.lifecycle import InvalidLifecycleTransitionError
from spindle.models import (
    ApprovalStatus,
    CanonStatus,
    Event,
    Project,
    SourceDocument,
    Suggestion,
)


@pytest.mark.asyncio
async def test_commit_service_non_destructive_and_provenance(test_session):
    """Test committing an approved suggestion creates non-colliding files and confirmed canon."""
    project = Project(name="Canon Universe")
    test_session.add(project)
    await test_session.commit()

    service = CanonCommitService(session=test_session)

    # 1. Simulate an existing document with the same expected path
    existing_doc = SourceDocument(
        project_id=project.id,
        file_path="Manuscript/Side Stories/The Secret Ledger.md",
        content_hash="existing_hash_123",
        document_type="scene",
        raw_content="Original existing file content.",
        parsed_metadata={},
    )
    test_session.add(existing_doc)
    await test_session.commit()

    # 2. Approved suggestion with the same title
    suggestion = Suggestion(
        project_id=project.id,
        suggestion_type="side_story",
        title="The Secret Ledger",
        premise="Elena discovers a second secret ledger hidden behind the archivist's desk.",
        detailed_content={
            "act": 2,
            "involved_characters": ["Elena Vareth", "Aldric Voss"],
            "scene_beats": [
                "Elena waits until the archivist leaves.",
                "She uncovers the bound ledger with royal seals.",
            ],
        },
        supporting_evidence=["Examples/The Loophole.md"],
        assumptions=["The archive door was unlocked."],
        validation_results={"overall_outcome": "PASS", "has_hard_failures": False},
        approval_status=ApprovalStatus.APPROVED.value,
    )
    test_session.add(suggestion)
    await test_session.commit()

    # Execute commit
    result = await service.commit_suggestion(
        suggestion=suggestion,
        destination_folder="Manuscript/Side Stories",
    )

    # Non-destructive check: since "The Secret Ledger.md" existed, must become "The Secret Ledger (2).md"
    assert result.file_path == "Manuscript/Side Stories/The Secret Ledger (2).md"
    assert result.document_id is not None
    assert result.event_id is not None

    # Verify original existing file content is unchanged
    original_check = (
        await test_session.execute(
            select(SourceDocument).where(
                SourceDocument.project_id == project.id,
                SourceDocument.file_path == "Manuscript/Side Stories/The Secret Ledger.md",
            )
        )
    ).scalar_one()
    assert original_check.raw_content == "Original existing file content."

    # Verify new canonical Event created
    event = (
        await test_session.execute(select(Event).where(Event.id == result.event_id))
    ).scalar_one()
    assert event.title == "The Secret Ledger"
    assert event.canon_status == CanonStatus.CONFIRMED.value
    assert "Elena Vareth" in event.participants
    assert event.source_document_id == result.document_id

    # Verify suggestion status updated to COMMITTED with audit trail
    assert suggestion.approval_status == ApprovalStatus.COMMITTED.value
    assert len(suggestion.detailed_content.get("audit_history", [])) == 1
    audit = suggestion.detailed_content["audit_history"][0]
    assert audit["action"] == "committed_to_canon"
    assert audit["destination_file_path"] == result.file_path


@pytest.mark.asyncio
async def test_commit_service_rejects_unapproved_suggestion(test_session):
    """Verify that committing a suggestion in PENDING_AUTHOR_APPROVAL or REJECTED raises an error."""
    project = Project(name="Guarded Universe")
    test_session.add(project)
    await test_session.commit()

    service = CanonCommitService(session=test_session)

    # Pending suggestion
    pending_sug = Suggestion(
        project_id=project.id,
        title="Unreviewed Proposal",
        premise="Some idea not yet reviewed.",
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL.value,
    )
    test_session.add(pending_sug)
    await test_session.commit()

    with pytest.raises(InvalidLifecycleTransitionError):
        await service.commit_suggestion(pending_sug)
