"""Story entity query endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.api.deps import get_current_project
from spindle.api.v1.schemas import EntitiesListResponse, EntitySummary
from spindle.database import get_db_session
from spindle.models.entity import Character, Location, WorldRule
from spindle.models.event import Event
from spindle.models.project import Project

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get(
    "",
    response_model=EntitiesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List extracted narrative entities",
)
async def list_entities(
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    entity_type: Annotated[str | None, Query(alias="type", description="Filter by type")] = None,
) -> EntitiesListResponse:
    """Retrieve indexed characters, events, locations, and world rules for the project."""
    target_type = entity_type.lower() if entity_type else None

    # Characters
    char_list: list[EntitySummary] = []
    if target_type is None or target_type == "character":
        char_stmt = select(Character).where(Character.project_id == project.id)
        chars = (await session.execute(char_stmt)).scalars().all()
        for c in chars:
            char_list.append(
                EntitySummary(
                    id=c.id,
                    name=c.name,
                    entity_type="character",
                    role_or_kind=c.role,
                    description=c.description,
                    canon_status=c.canon_status,
                    aliases=c.aliases,
                    metadata=c.metadata_json,
                )
            )

    # Events
    event_list: list[EntitySummary] = []
    if target_type is None or target_type == "event":
        evt_stmt = select(Event).where(Event.project_id == project.id)
        events = (await session.execute(evt_stmt)).scalars().all()
        for e in events:
            event_list.append(
                EntitySummary(
                    id=e.id,
                    name=e.title,
                    entity_type="event",
                    role_or_kind=e.chronological_timestamp,
                    description=e.description,
                    canon_status=e.canon_status,
                    aliases=[],
                    metadata={
                        "narrative_position": e.narrative_position,
                        "chronological_order": e.chronological_order,
                        "participants": e.participants,
                    },
                )
            )

    # Locations
    loc_list: list[EntitySummary] = []
    if target_type is None or target_type == "location":
        loc_stmt = select(Location).where(Location.project_id == project.id)
        locs = (await session.execute(loc_stmt)).scalars().all()
        for loc in locs:
            loc_list.append(
                EntitySummary(
                    id=loc.id,
                    name=loc.name,
                    entity_type="location",
                    role_or_kind=loc.kind,
                    description=loc.description,
                    canon_status="confirmed",
                    aliases=[],
                    metadata={"region": loc.region, "attributes": loc.attributes},
                )
            )

    # World Rules
    rule_list: list[EntitySummary] = []
    if target_type is None or target_type in ("world_rule", "rule", "magic"):
        rule_stmt = select(WorldRule).where(WorldRule.project_id == project.id)
        rules = (await session.execute(rule_stmt)).scalars().all()
        for r in rules:
            rule_list.append(
                EntitySummary(
                    id=r.id,
                    name=r.name,
                    entity_type="world_rule",
                    role_or_kind=r.rule_type,
                    description=r.description,
                    canon_status="confirmed",
                    aliases=[],
                    metadata={
                        "enforcement_level": r.enforcement_level,
                        **r.metadata_json,
                    },
                )
            )

    return EntitiesListResponse(
        project_id=project.id,
        characters=char_list,
        events=event_list,
        locations=loc_list,
        world_rules=rule_list,
    )


@router.get(
    "/{entity_id}",
    response_model=EntitySummary,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific narrative entity",
)
async def get_entity(
    entity_id: uuid.UUID,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EntitySummary:
    """Retrieve a single entity by UUID across characters, events, locations, and rules."""
    # Try Character
    c_stmt = select(Character).where(Character.id == entity_id, Character.project_id == project.id)
    char = (await session.execute(c_stmt)).scalar_one_or_none()
    if char:
        return EntitySummary(
            id=char.id,
            name=char.name,
            entity_type="character",
            role_or_kind=char.role,
            description=char.description,
            canon_status=char.canon_status,
            aliases=char.aliases,
            metadata=char.metadata_json,
        )

    # Try Event
    e_stmt = select(Event).where(Event.id == entity_id, Event.project_id == project.id)
    event = (await session.execute(e_stmt)).scalar_one_or_none()
    if event:
        return EntitySummary(
            id=event.id,
            name=event.title,
            entity_type="event",
            role_or_kind=event.chronological_timestamp,
            description=event.description,
            canon_status=event.canon_status,
            aliases=[],
            metadata={
                "narrative_position": event.narrative_position,
                "chronological_order": event.chronological_order,
                "participants": event.participants,
            },
        )

    # Try Location
    l_stmt = select(Location).where(Location.id == entity_id, Location.project_id == project.id)
    loc = (await session.execute(l_stmt)).scalar_one_or_none()
    if loc:
        return EntitySummary(
            id=loc.id,
            name=loc.name,
            entity_type="location",
            role_or_kind=loc.kind,
            description=loc.description,
            canon_status="confirmed",
            aliases=[],
            metadata={"region": loc.region, "attributes": loc.attributes},
        )

    # Try World Rule
    r_stmt = select(WorldRule).where(WorldRule.id == entity_id, WorldRule.project_id == project.id)
    rule = (await session.execute(r_stmt)).scalar_one_or_none()
    if rule:
        return EntitySummary(
            id=rule.id,
            name=rule.name,
            entity_type="world_rule",
            role_or_kind=rule.rule_type,
            description=rule.description,
            canon_status="confirmed",
            aliases=[],
            metadata={"enforcement_level": rule.enforcement_level, **rule.metadata_json},
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
