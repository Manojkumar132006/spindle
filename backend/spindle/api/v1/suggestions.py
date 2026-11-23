"""Suggestion retrieval, inspection, lifecycle transitions, and canon commitment endpoints."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.api.deps import get_current_project
from spindle.api.v1.generate import SuggestionResponse
from spindle.core.commit_service import CanonCommitService
from spindle.core.lifecycle import (
    InvalidLifecycleTransitionError,
    validate_lifecycle_transition,
)
from spindle.database import get_db_session
from spindle.models.base import ApprovalStatus
from spindle.models.project import Project
from spindle.models.suggestion import Suggestion, SuggestionRevision

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


class ApproveSuggestionRequest(BaseModel):
    """Payload for approving a suggestion."""

    notes: str | None = Field(default=None, description="Optional author approval notes")


class RejectSuggestionRequest(BaseModel):
    """Payload for rejecting a suggestion with mandatory rationale."""

    reason: str = Field(
        min_length=3,
        description="Mandatory reason explaining why the suggestion was rejected",
    )


class EditSuggestionRequest(BaseModel):
    """Payload for author modifications to a suggestion."""

    title: str | None = Field(default=None, description="Updated suggestion title")
    premise: str | None = Field(default=None, description="Updated premise")
    detailed_content: dict[str, Any] | None = Field(
        default=None, description="Updated detailed beats/structure"
    )
    edit_summary: str | None = Field(
        default="Author manual edits", description="Summary of adjustments made"
    )


class CommitSuggestionRequest(BaseModel):
    """Payload for committing an approved suggestion to vault canon."""

    destination_folder: str = Field(
        default="Manuscript/Side Stories",
        description="Target directory in Obsidian vault",
    )


class CommitSuggestionResponse(BaseModel):
    """Response returned after non-destructive canon commitment."""

    status: str
    suggestion_id: uuid.UUID
    project_id: uuid.UUID
    file_path: str
    content_hash: str
    document_id: uuid.UUID
    event_id: uuid.UUID
    markdown_content: str
    committed_at: datetime


@router.get(
    "",
    response_model=list[SuggestionResponse],
    status_code=status.HTTP_200_OK,
    summary="List generated suggestions",
)
async def list_suggestions(
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    approval_status: Annotated[
        str | None, Query(alias="status", description="Filter by approval status")
    ] = None,
    suggestion_type: Annotated[
        str | None, Query(alias="type", description="Filter by suggestion type")
    ] = None,
) -> list[SuggestionResponse]:
    """Retrieve suggestions created for the active project."""
    stmt = select(Suggestion).where(Suggestion.project_id == project.id)

    if approval_status:
        stmt = stmt.where(Suggestion.approval_status == approval_status.lower())
    if suggestion_type:
        stmt = stmt.where(Suggestion.suggestion_type == suggestion_type.lower())

    stmt = stmt.order_by(Suggestion.created_at.desc())
    suggestions = (await session.execute(stmt)).scalars().all()

    return [
        SuggestionResponse(
            id=s.id,
            project_id=s.project_id,
            suggestion_type=s.suggestion_type,
            title=s.title,
            premise=s.premise,
            detailed_content=s.detailed_content,
            supporting_evidence=s.supporting_evidence,
            assumptions=s.assumptions,
            validation_results=s.validation_results,
            approval_status=s.approval_status,
            branch_id=s.branch_id,
        )
        for s in suggestions
    ]


@router.get(
    "/{suggestion_id}",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific suggestion",
)
async def get_suggestion(
    suggestion_id: uuid.UUID,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SuggestionResponse:
    """Retrieve a single generated suggestion along with its validation report and citations."""
    stmt = select(Suggestion).where(
        Suggestion.id == suggestion_id, Suggestion.project_id == project.id
    )
    s = (await session.execute(stmt)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    return SuggestionResponse(
        id=s.id,
        project_id=s.project_id,
        suggestion_type=s.suggestion_type,
        title=s.title,
        premise=s.premise,
        detailed_content=s.detailed_content,
        supporting_evidence=s.supporting_evidence,
        assumptions=s.assumptions,
        validation_results=s.validation_results,
        approval_status=s.approval_status,
        branch_id=s.branch_id,
    )


@router.post(
    "/{suggestion_id}/approve",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a generated suggestion",
)
async def approve_suggestion(
    suggestion_id: uuid.UUID,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    payload: ApproveSuggestionRequest | None = None,
) -> SuggestionResponse:
    """Transition suggestion to APPROVED status after author inspection."""
    if payload is None:
        payload = ApproveSuggestionRequest()

    stmt = select(Suggestion).where(
        Suggestion.id == suggestion_id, Suggestion.project_id == project.id
    )
    s = (await session.execute(stmt)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    try:
        validate_lifecycle_transition(s.approval_status, ApprovalStatus.APPROVED)
    except InvalidLifecycleTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    s.approval_status = ApprovalStatus.APPROVED.value
    if payload.notes:
        history = s.detailed_content.get("author_notes", [])
        history.append(payload.notes)
        s.detailed_content["author_notes"] = history

    await session.commit()
    await session.refresh(s)

    return SuggestionResponse(
        id=s.id,
        project_id=s.project_id,
        suggestion_type=s.suggestion_type,
        title=s.title,
        premise=s.premise,
        detailed_content=s.detailed_content,
        supporting_evidence=s.supporting_evidence,
        assumptions=s.assumptions,
        validation_results=s.validation_results,
        approval_status=s.approval_status,
        branch_id=s.branch_id,
    )


@router.post(
    "/{suggestion_id}/reject",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a suggestion with mandatory reason",
)
async def reject_suggestion(
    suggestion_id: uuid.UUID,
    payload: RejectSuggestionRequest,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SuggestionResponse:
    """Transition suggestion to REJECTED status, logging the author's rejection rationale."""
    stmt = select(Suggestion).where(
        Suggestion.id == suggestion_id, Suggestion.project_id == project.id
    )
    s = (await session.execute(stmt)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    try:
        validate_lifecycle_transition(s.approval_status, ApprovalStatus.REJECTED)
    except InvalidLifecycleTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    s.approval_status = ApprovalStatus.REJECTED.value
    s.rejection_reason = payload.reason

    await session.commit()
    await session.refresh(s)

    return SuggestionResponse(
        id=s.id,
        project_id=s.project_id,
        suggestion_type=s.suggestion_type,
        title=s.title,
        premise=s.premise,
        detailed_content=s.detailed_content,
        supporting_evidence=s.supporting_evidence,
        assumptions=s.assumptions,
        validation_results=s.validation_results,
        approval_status=s.approval_status,
        branch_id=s.branch_id,
    )


@router.put(
    "/{suggestion_id}/edit",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit suggestion and record historical revision",
)
async def edit_suggestion(
    suggestion_id: uuid.UUID,
    payload: EditSuggestionRequest,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SuggestionResponse:
    """Apply author modifications to a suggestion while archiving previous revision."""
    stmt = select(Suggestion).where(
        Suggestion.id == suggestion_id, Suggestion.project_id == project.id
    )
    s = (await session.execute(stmt)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    try:
        validate_lifecycle_transition(s.approval_status, ApprovalStatus.EDITED)
    except InvalidLifecycleTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Count existing revisions
    rev_count_stmt = select(func.count(SuggestionRevision.id)).where(
        SuggestionRevision.suggestion_id == s.id
    )
    rev_count = (await session.execute(rev_count_stmt)).scalar() or 0

    # Archive previous content into SuggestionRevision
    archive_revision = SuggestionRevision(
        suggestion_id=s.id,
        revision_number=rev_count + 1,
        content={"title": s.title, "premise": s.premise, **s.detailed_content},
        validation_results=s.validation_results,
        revision_reason=payload.edit_summary,
    )
    session.add(archive_revision)

    # Apply edits
    if payload.title is not None:
        s.title = payload.title
    if payload.premise is not None:
        s.premise = payload.premise
    if payload.detailed_content is not None:
        s.detailed_content = payload.detailed_content

    s.author_edits = payload.edit_summary
    s.approval_status = ApprovalStatus.EDITED.value

    await session.commit()
    await session.refresh(s)

    return SuggestionResponse(
        id=s.id,
        project_id=s.project_id,
        suggestion_type=s.suggestion_type,
        title=s.title,
        premise=s.premise,
        detailed_content=s.detailed_content,
        supporting_evidence=s.supporting_evidence,
        assumptions=s.assumptions,
        validation_results=s.validation_results,
        approval_status=s.approval_status,
        branch_id=s.branch_id,
    )


@router.post(
    "/{suggestion_id}/commit",
    response_model=CommitSuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Commit an approved suggestion to author canon",
)
async def commit_suggestion(
    suggestion_id: uuid.UUID,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    payload: CommitSuggestionRequest | None = None,
) -> CommitSuggestionResponse:
    """Non-destructively write approved suggestion as an Obsidian document and record canon event."""
    if payload is None:
        payload = CommitSuggestionRequest()

    stmt = select(Suggestion).where(
        Suggestion.id == suggestion_id, Suggestion.project_id == project.id
    )
    s = (await session.execute(stmt)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    # Ensure suggestion is in an approvable state (approved or edited)
    if s.approval_status not in (ApprovalStatus.APPROVED.value, ApprovalStatus.EDITED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot commit suggestion with status '{s.approval_status}'. "
                "Suggestion must be APPROVED or EDITED before commitment to canon."
            ),
        )

    commit_service = CanonCommitService(session=session)
    result = await commit_service.commit_suggestion(
        suggestion=s,
        destination_folder=payload.destination_folder,
    )

    return CommitSuggestionResponse(
        status="committed",
        suggestion_id=result.suggestion_id,
        project_id=result.project_id,
        file_path=result.file_path,
        content_hash=result.content_hash,
        document_id=result.document_id,
        event_id=result.event_id,
        markdown_content=result.markdown_content,
        committed_at=result.committed_at,
    )
