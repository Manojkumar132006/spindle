"""Integration tests for suggestion review, edit, reject, and canon commit endpoints."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from spindle.api.app import app
from spindle.database import get_db_session
from spindle.models.base import ApprovalStatus, CanonStatus
from spindle.models.document import SourceDocument
from spindle.models.event import Event
from spindle.models.project import Project
from spindle.models.suggestion import Suggestion, SuggestionRevision


@pytest.fixture
def override_db_session(test_session):
    """Override get_db_session FastAPI dependency with test_session."""

    async def _override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_approve_and_commit_flow(override_db_session, test_session):
    """Test standard approval lifecycle followed by non-destructive canon commitment."""
    project = Project(name="Lifecycle Test Project")
    test_session.add(project)
    await test_session.commit()

    suggestion = Suggestion(
        project_id=project.id,
        suggestion_type="side_story",
        title="The Midnight Accord",
        premise="Elena meets with the northern envoys in secret.",
        detailed_content={
            "involved_characters": ["Elena Vareth"],
            "scene_beats": ["Elena slips past guards.", "The treaty is signed."],
        },
        supporting_evidence=["Timeline/Treaty.md"],
        assumptions=["Guards were bribed."],
        validation_results={"overall_outcome": "PASS", "has_hard_failures": False},
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL.value,
    )
    test_session.add(suggestion)
    await test_session.commit()

    headers = {"X-Project-ID": str(project.id)}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Approve the suggestion
        approve_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/approve",
            json={"notes": "Approved for inclusion in Chapter 4."},
            headers=headers,
        )
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["approval_status"] == ApprovalStatus.APPROVED.value

        # 2. Commit the approved suggestion
        commit_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/commit",
            json={"destination_folder": "Manuscript/Side Stories"},
            headers=headers,
        )
        assert commit_resp.status_code == 200
        commit_data = commit_resp.json()
        assert commit_data["status"] == "committed"
        assert commit_data["file_path"] == "Manuscript/Side Stories/The Midnight Accord.md"
        assert commit_data["document_id"] is not None
        assert commit_data["event_id"] is not None
        assert "# The Midnight Accord" in commit_data["markdown_content"]
        assert "Elena slips past guards." in commit_data["markdown_content"]

        # Verify DB records
        doc = (
            await test_session.execute(
                select(SourceDocument).where(
                    SourceDocument.id == uuid.UUID(commit_data["document_id"])
                )
            )
        ).scalar_one()
        assert doc.file_path == "Manuscript/Side Stories/The Midnight Accord.md"

        event = (
            await test_session.execute(
                select(Event).where(Event.id == uuid.UUID(commit_data["event_id"]))
            )
        ).scalar_one()
        assert event.canon_status == CanonStatus.CONFIRMED.value
        assert "Elena Vareth" in event.participants

        # 3. Test non-destructive collision avoidance:
        # Create a second suggestion with the same title, approve, and commit
        second_suggestion = Suggestion(
            project_id=project.id,
            suggestion_type="side_story",
            title="The Midnight Accord",
            premise="Alternative perspective on the midnight meeting.",
            detailed_content={"scene_beats": ["Aldric watches from the balcony."]},
            validation_results={"overall_outcome": "PASS", "has_hard_failures": False},
            approval_status=ApprovalStatus.APPROVED.value,
        )
        test_session.add(second_suggestion)
        await test_session.commit()

        second_commit_resp = await client.post(
            f"/api/v1/suggestions/{second_suggestion.id}/commit",
            json={"destination_folder": "Manuscript/Side Stories"},
            headers=headers,
        )
        assert second_commit_resp.status_code == 200
        second_commit_data = second_commit_resp.json()
        # Non-destructive file naming: appends suffix (2)
        assert (
            second_commit_data["file_path"] == "Manuscript/Side Stories/The Midnight Accord (2).md"
        )


@pytest.mark.asyncio
async def test_edit_and_revision_history_flow(override_db_session, test_session):
    """Test author editing a suggestion, recording revisions, and committing."""
    project = Project(name="Edit Test Project")
    test_session.add(project)
    await test_session.commit()

    suggestion = Suggestion(
        project_id=project.id,
        suggestion_type="plot_point",
        title="Draft Plot Point",
        premise="Initial premise generated by agent.",
        detailed_content={"beat": "Elena encounters a stranger."},
        validation_results={"overall_outcome": "PASS", "has_hard_failures": False},
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL.value,
    )
    test_session.add(suggestion)
    await test_session.commit()

    headers = {"X-Project-ID": str(project.id)}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Edit the suggestion
        edit_payload = {
            "title": "Refined Plot Point: The Meeting at Dusk",
            "premise": "Elena meets the envoy disguised as a traveling merchant.",
            "detailed_content": {
                "beat": "Elena notices the seal on the merchant's ring.",
                "involved_characters": ["Elena Vareth", "Merchant Envoy"],
            },
            "edit_summary": "Sharpened dramatic stakes and disguise details.",
        }
        edit_resp = await client.put(
            f"/api/v1/suggestions/{suggestion.id}/edit",
            json=edit_payload,
            headers=headers,
        )
        assert edit_resp.status_code == 200
        edit_data = edit_resp.json()
        assert edit_data["approval_status"] == ApprovalStatus.EDITED.value
        assert edit_data["title"] == "Refined Plot Point: The Meeting at Dusk"
        assert edit_data["premise"] == "Elena meets the envoy disguised as a traveling merchant."

        # Verify SuggestionRevision archived
        revisions = (
            (
                await test_session.execute(
                    select(SuggestionRevision).where(
                        SuggestionRevision.suggestion_id == suggestion.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(revisions) == 1
        assert revisions[0].revision_number == 1
        assert revisions[0].content["title"] == "Draft Plot Point"
        assert revisions[0].revision_reason == "Sharpened dramatic stakes and disguise details."

        # 2. Commit the edited suggestion
        commit_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/commit",
            headers=headers,
        )
        assert commit_resp.status_code == 200
        commit_data = commit_resp.json()
        assert "The Meeting at Dusk" in commit_data["file_path"]
        assert "Elena notices the seal on the merchant's ring." in commit_data["markdown_content"]


@pytest.mark.asyncio
async def test_reject_flow(override_db_session, test_session):
    """Test rejection with mandatory explanation and transition guards."""
    project = Project(name="Reject Test Project")
    test_session.add(project)
    await test_session.commit()

    suggestion = Suggestion(
        project_id=project.id,
        suggestion_type="plot_point",
        title="Unwanted Suggestion",
        premise="Elena decides to abandon the city entirely.",
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL.value,
    )
    test_session.add(suggestion)
    await test_session.commit()

    headers = {"X-Project-ID": str(project.id)}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Missing or too short reason fails validation
        invalid_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/reject",
            json={"reason": "no"},
            headers=headers,
        )
        assert invalid_resp.status_code == 422

        # 2. Proper rejection
        reject_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/reject",
            json={"reason": "OOC: Elena would never abandon the lower districts in winter."},
            headers=headers,
        )
        assert reject_resp.status_code == 200
        reject_data = reject_resp.json()
        assert reject_data["approval_status"] == ApprovalStatus.REJECTED.value

        # 3. Attempting to commit a REJECTED suggestion returns 400
        commit_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/commit",
            headers=headers,
        )
        assert commit_resp.status_code == 400
        assert "Cannot commit suggestion with status 'rejected'" in commit_resp.json()["detail"]


@pytest.mark.asyncio
async def test_lifecycle_transition_guards_api(override_db_session, test_session):
    """Test API safeguards against illegal transitions and unapproved commits."""
    project = Project(name="Guards Test Project")
    test_session.add(project)
    await test_session.commit()

    # Unreviewed suggestion (PENDING_AUTHOR_APPROVAL)
    suggestion = Suggestion(
        project_id=project.id,
        suggestion_type="side_story",
        title="Unreviewed Arc",
        premise="Some unapproved proposal.",
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL.value,
    )
    test_session.add(suggestion)
    await test_session.commit()

    headers = {"X-Project-ID": str(project.id)}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Cannot commit without prior approve or edit
        commit_resp = await client.post(
            f"/api/v1/suggestions/{suggestion.id}/commit",
            headers=headers,
        )
        assert commit_resp.status_code == 400
        assert "Suggestion must be APPROVED or EDITED" in commit_resp.json()["detail"]

        # Non-existent suggestion returns 404
        random_id = uuid.uuid4()
        not_found_resp = await client.post(
            f"/api/v1/suggestions/{random_id}/approve",
            headers=headers,
        )
        assert not_found_resp.status_code == 404
