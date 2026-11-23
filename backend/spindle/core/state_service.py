"""Narrative State Service assembling point-in-time story state snapshots."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spindle.models.base import CanonStatus, ThreadStatus
from spindle.models.constraint import Constraint
from spindle.models.entity import Character, Location, Relationship, WorldRule
from spindle.models.event import Event, NarrativeThread
from spindle.models.knowledge import CharacterKnowledge


@dataclass
class StoryState:
    """Point-in-time snapshot of the narrative universe at a specific narrative position."""

    project_id: uuid.UUID
    narrative_position: float
    branch_id: uuid.UUID | None = None
    characters: list[Character] = field(default_factory=list)
    established_events: list[Event] = field(default_factory=list)
    active_world_rules: list[WorldRule] = field(default_factory=list)
    active_constraints: list[Constraint] = field(default_factory=list)
    open_threads: list[NarrativeThread] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    character_knowledge: dict[uuid.UUID, list[CharacterKnowledge]] = field(default_factory=dict)

    # Index caches
    _character_by_id: dict[uuid.UUID, Character] = field(init=False, default_factory=dict)
    _character_by_name: dict[str, Character] = field(init=False, default_factory=dict)
    _events_by_id: dict[uuid.UUID, Event] = field(init=False, default_factory=dict)
    _events_by_title: dict[str, Event] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        """Build fast lookup indices."""
        for char in self.characters:
            self._character_by_id[char.id] = char
            self._character_by_name[char.name.lower()] = char
            for alias in char.aliases or []:
                if isinstance(alias, str):
                    self._character_by_name[alias.lower()] = char

        for ev in self.established_events:
            self._events_by_id[ev.id] = ev
            self._events_by_title[ev.title.lower()] = ev

    @property
    def chronological_events(self) -> list[Event]:
        """Return established events sorted by chronological order (decoupled from narrative position)."""
        return sorted(
            self.established_events,
            key=lambda e: (
                e.chronological_order if e.chronological_order is not None else float("inf"),
                e.narrative_position,
            ),
        )

    def get_character(self, identifier: str | uuid.UUID) -> Character | None:
        """Find a character by UUID or name/alias (case-insensitive)."""
        if isinstance(identifier, uuid.UUID):
            return self._character_by_id.get(identifier)
        try:
            parsed_uuid = uuid.UUID(str(identifier))
            if parsed_uuid in self._character_by_id:
                return self._character_by_id[parsed_uuid]
        except (ValueError, AttributeError):
            pass
        return self._character_by_name.get(str(identifier).lower())

    def get_event(self, identifier: str | uuid.UUID) -> Event | None:
        """Find an established event by UUID or title (case-insensitive)."""
        if isinstance(identifier, uuid.UUID):
            return self._events_by_id.get(identifier)
        try:
            parsed_uuid = uuid.UUID(str(identifier))
            if parsed_uuid in self._events_by_id:
                return self._events_by_id[parsed_uuid]
        except (ValueError, AttributeError):
            pass
        return self._events_by_title.get(str(identifier).lower())

    def is_character_alive(self, identifier: str | uuid.UUID) -> bool:
        """Check if character is considered alive at this point in the narrative."""
        char = self.get_character(identifier)
        if not char:
            return False

        # First check explicitly recorded current_state
        if char.current_state and char.current_state.lower() in ("dead", "deceased", "killed"):
            return False

        # Next check if any established event marked them dead or killed them
        char_id_str = str(char.id)
        char_name_lower = char.name.lower()

        for ev in self.established_events:
            meta = ev.metadata_json or {}
            # Check state changes metadata
            state_changes = meta.get("character_state_changes", {})
            if state_changes.get(char_id_str) in (
                "dead",
                "deceased",
                "killed",
            ) or state_changes.get(char_name_lower) in ("dead", "deceased", "killed"):
                return False

            # Check fatal event tags
            deaths = meta.get("deaths", [])
            if char_id_str in deaths or char_name_lower in [str(d).lower() for d in deaths]:
                return False

        return True

    def get_character_knowledge(
        self,
        character_identifier: str | uuid.UUID,
        fact_or_event_id: str | None = None,
    ) -> list[CharacterKnowledge]:
        """Get knowledge items possessed by a character at this point in time."""
        char = self.get_character(character_identifier)
        if not char or char.id not in self.character_knowledge:
            return []

        items = self.character_knowledge[char.id]
        if fact_or_event_id:
            fact_lower = fact_or_event_id.lower()
            return [it for it in items if it.fact_or_event_id.lower() == fact_lower]
        return items


class NarrativeStateService:
    """Service responsible for querying and assembling point-in-time story state snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_story_state(
        self,
        project_id: uuid.UUID,
        narrative_position: float,
        branch_id: uuid.UUID | None = None,
    ) -> StoryState:
        """Assemble point-in-time state snapshot at the specified narrative position."""
        # 1. Query characters
        char_stmt = (
            select(Character)
            .where(
                Character.project_id == project_id,
                Character.canon_status != CanonStatus.REJECTED.value,
            )
            .order_by(Character.name.asc())
        )
        char_res = await self.session.execute(char_stmt)
        characters = list(char_res.scalars().all())

        # 2. Query established events: narrative_position <= requested narrative_position
        event_stmt = (
            select(Event)
            .where(
                Event.project_id == project_id,
                Event.narrative_position <= narrative_position,
                Event.canon_status != CanonStatus.REJECTED.value,
            )
            .order_by(Event.narrative_position.asc())
        )
        event_res = await self.session.execute(event_stmt)
        established_events = list(event_res.scalars().all())

        # 3. Query active world rules
        rules_stmt = (
            select(WorldRule)
            .where(
                WorldRule.project_id == project_id,
            )
            .order_by(WorldRule.name.asc())
        )
        rules_res = await self.session.execute(rules_stmt)
        active_world_rules = list(rules_res.scalars().all())

        # 4. Query active constraints
        constraints_stmt = (
            select(Constraint)
            .where(
                Constraint.project_id == project_id,
                Constraint.active.is_(True),
            )
            .order_by(Constraint.name.asc())
        )
        constraints_res = await self.session.execute(constraints_stmt)
        active_constraints = list(constraints_res.scalars().all())

        # 5. Query open narrative threads: introduced at or before narrative_position and not resolved before it
        threads_stmt = (
            select(NarrativeThread)
            .options(
                selectinload(NarrativeThread.introduction_event),
                selectinload(NarrativeThread.resolution_event),
            )
            .where(
                NarrativeThread.project_id == project_id,
                NarrativeThread.status != ThreadStatus.ABANDONED.value,
            )
        )
        threads_res = await self.session.execute(threads_stmt)
        raw_threads = list(threads_res.scalars().all())

        open_threads: list[NarrativeThread] = []
        for thread in raw_threads:
            # Check introduction threshold
            intro_pos = (
                thread.introduction_event.narrative_position
                if thread.introduction_event
                else float("-inf")
            )
            if intro_pos > narrative_position:
                continue  # Not yet introduced in this narrative position

            # Check resolution threshold
            if (
                thread.resolution_event
                and thread.resolution_event.narrative_position <= narrative_position
            ):
                continue  # Already resolved prior to this narrative position

            open_threads.append(thread)

        # 6. Query locations and relationships
        loc_stmt = select(Location).where(Location.project_id == project_id)
        loc_res = await self.session.execute(loc_stmt)
        locations = list(loc_res.scalars().all())

        rel_stmt = (
            select(Relationship)
            .options(
                selectinload(Relationship.source_character),
                selectinload(Relationship.target_character),
            )
            .where(Relationship.project_id == project_id)
        )
        rel_res = await self.session.execute(rel_stmt)
        relationships = list(rel_res.scalars().all())

        # 7. Assemble character knowledge up to this narrative position
        # Acquired at or before narrative_position
        char_ids = [c.id for c in characters]
        knowledge_by_char: dict[uuid.UUID, list[CharacterKnowledge]] = {
            c_id: [] for c_id in char_ids
        }

        if char_ids:
            knowledge_stmt = (
                select(CharacterKnowledge)
                .options(selectinload(CharacterKnowledge.source_event))
                .where(
                    CharacterKnowledge.character_id.in_(char_ids),
                )
            )
            k_res = await self.session.execute(knowledge_stmt)
            all_knowledge = list(k_res.scalars().all())

            for k_item in all_knowledge:
                # Validate acquisition position
                acq_pos = k_item.acquired_at
                if acq_pos is None and k_item.source_event:
                    acq_pos = k_item.source_event.narrative_position
                if acq_pos is None:
                    acq_pos = 0.0

                if acq_pos <= narrative_position:
                    knowledge_by_char[k_item.character_id].append(k_item)

        return StoryState(
            project_id=project_id,
            narrative_position=narrative_position,
            branch_id=branch_id,
            characters=characters,
            established_events=established_events,
            active_world_rules=active_world_rules,
            active_constraints=active_constraints,
            open_threads=open_threads,
            locations=locations,
            relationships=relationships,
            character_knowledge=knowledge_by_char,
        )


async def get_story_state(
    session: AsyncSession,
    project_id: uuid.UUID,
    narrative_position: float,
    branch_id: uuid.UUID | None = None,
) -> StoryState:
    """Convenience function to instantiate service and retrieve story state snapshot."""
    service = NarrativeStateService(session)
    return await service.get_story_state(project_id, narrative_position, branch_id)
