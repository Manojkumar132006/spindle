"""Story overview and narrative universe status endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.api.deps import get_current_project
from spindle.api.v1.schemas import StoryOverviewResponse
from spindle.database import get_db_session
from spindle.models.base import ThreadStatus
from spindle.models.constraint import Constraint
from spindle.models.document import SourceDocument
from spindle.models.entity import Character, Location, WorldRule
from spindle.models.event import Event, NarrativeThread
from spindle.models.project import Project

router = APIRouter(prefix="/story", tags=["Story"])


@router.get(
    "/overview",
    response_model=StoryOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get story overview metrics",
)
async def get_story_overview(
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoryOverviewResponse:
    """Retrieve high-level story metrics for the Obsidian side panel."""
    # Characters count
    char_count = (
        await session.execute(
            select(func.count(Character.id)).where(Character.project_id == project.id)
        )
    ).scalar() or 0

    # Events count
    evt_count = (
        await session.execute(select(func.count(Event.id)).where(Event.project_id == project.id))
    ).scalar() or 0

    # Locations count
    loc_count = (
        await session.execute(
            select(func.count(Location.id)).where(Location.project_id == project.id)
        )
    ).scalar() or 0

    # World rules count
    rule_count = (
        await session.execute(
            select(func.count(WorldRule.id)).where(WorldRule.project_id == project.id)
        )
    ).scalar() or 0

    # Active constraints count
    constraint_count = (
        await session.execute(
            select(func.count(Constraint.id)).where(
                Constraint.project_id == project.id, Constraint.active.is_(True)
            )
        )
    ).scalar() or 0

    # Open narrative threads count
    thread_count = (
        await session.execute(
            select(func.count(NarrativeThread.id)).where(
                NarrativeThread.project_id == project.id,
                NarrativeThread.status == ThreadStatus.OPEN.value,
            )
        )
    ).scalar() or 0

    # Documents count & latest index date
    doc_count = (
        await session.execute(
            select(func.count(SourceDocument.id)).where(SourceDocument.project_id == project.id)
        )
    ).scalar() or 0

    latest_date = (
        await session.execute(
            select(SourceDocument.indexed_at)
            .where(SourceDocument.project_id == project.id)
            .order_by(SourceDocument.indexed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return StoryOverviewResponse(
        project_id=project.id,
        project_name=project.name,
        description=project.description,
        characters_count=char_count,
        character_count=char_count,
        events_count=evt_count,
        event_count=evt_count,
        locations_count=loc_count,
        location_count=loc_count,
        world_rules_count=rule_count,
        constraints_count=constraint_count,
        active_constraints=constraint_count,
        open_threads_count=thread_count,
        unresolved_threads=thread_count,
        documents_count=doc_count,
        total_documents=doc_count,
        last_synced_at=latest_date,
    )
