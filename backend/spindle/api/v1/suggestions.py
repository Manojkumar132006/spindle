"""Suggestion retrieval and inspection endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.api.deps import get_current_project
from spindle.api.v1.generate import SuggestionResponse
from spindle.database import get_db_session
from spindle.models.project import Project
from spindle.models.suggestion import Suggestion

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


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
