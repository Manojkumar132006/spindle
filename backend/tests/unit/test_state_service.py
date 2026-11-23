"""Unit tests for the Narrative State Service (Task 3.1)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.core.state_service import StoryState, get_story_state
from spindle.models.base import EnforcementLevel, RuleType, ThreadStatus
from spindle.models.constraint import Constraint
from spindle.models.entity import Character, Location, WorldRule
from spindle.models.event import Event, NarrativeThread
from spindle.models.project import Project


@pytest.fixture
async def seeded_project(test_session: AsyncSession):
    """Seed test project with characters, events, threads, rules, and constraints across timeline."""
    proj = Project(name="State Test Universe", description="Testing point-in-time state")
    test_session.add(proj)
    await test_session.flush()

    # Characters
    c1 = Character(
        project_id=proj.id,
        name="Elena Vance",
        aliases=["Vance", "The Oracle"],
        current_state="alive",
    )
    c2 = Character(
        project_id=proj.id,
        name="Lord Malakar",
        aliases=["Malakar"],
        current_state="alive",
    )
    test_session.add_all([c1, c2])
    await test_session.flush()

    # Locations
    loc = Location(project_id=proj.id, name="Obsidian Citadel", kind="fortress")
    test_session.add(loc)
    await test_session.flush()

    # Events at different narrative and chronological positions
    # Flashback: scene 1.0, but happens chronologically at 100.0 (past)
    e1 = Event(
        project_id=proj.id,
        title="Ancient Treaty Signed",
        narrative_position=1.0,
        chronological_order=10.0,
        location_id=loc.id,
        participants=[str(c1.id)],
    )
    # Scene 2.0: Malakar ambushed
    e2 = Event(
        project_id=proj.id,
        title="Citadel Siege",
        narrative_position=2.0,
        chronological_order=50.0,
        location_id=loc.id,
        participants=[str(c1.id), str(c2.id)],
    )
    # Scene 3.0: Malakar is killed
    e3 = Event(
        project_id=proj.id,
        title="Fall of Malakar",
        narrative_position=3.0,
        chronological_order=60.0,
        location_id=loc.id,
        participants=[str(c2.id)],
        metadata_json={
            "character_state_changes": {str(c2.id): "dead"},
            "deaths": [str(c2.id)],
        },
    )
    # Scene 4.0: Aftermath
    e4 = Event(
        project_id=proj.id,
        title="Aftermath and Mourning",
        narrative_position=4.0,
        chronological_order=70.0,
        participants=[str(c1.id)],
    )
    test_session.add_all([e1, e2, e3, e4])
    await test_session.flush()

    # Narrative Thread introduced at e2, resolved at e4
    thread = NarrativeThread(
        project_id=proj.id,
        title="Who Betrayed the Citadel?",
        status=ThreadStatus.OPEN.value,
        introduction_event_id=e2.id,
        resolution_event_id=e4.id,
    )
    test_session.add(thread)

    # World Rule
    rule = WorldRule(
        project_id=proj.id,
        name="Rule of Blood Magic",
        description="Blood magic requires life sacrifice",
        rule_type=RuleType.MAGIC.value,
        enforcement_level=EnforcementLevel.HARD.value,
    )
    test_session.add(rule)

    # Active Constraint
    constraint = Constraint(
        project_id=proj.id,
        name="No FTL Travel",
        description="Faster than light travel does not exist",
        active=True,
    )
    test_session.add(constraint)
    await test_session.flush()

    return {
        "project": proj,
        "elena": c1,
        "malakar": c2,
        "events": [e1, e2, e3, e4],
        "thread": thread,
    }


@pytest.mark.asyncio
async def test_narrative_state_at_scene_2(test_session: AsyncSession, seeded_project):
    """Verify story state snapshot at narrative position 2.0."""
    proj = seeded_project["project"]
    state = await get_story_state(test_session, proj.id, narrative_position=2.0)

    assert isinstance(state, StoryState)
    assert state.narrative_position == 2.0
    # At scene 2.0, only e1 and e2 are established
    assert len(state.established_events) == 2
    titles = [e.title for e in state.established_events]
    assert "Ancient Treaty Signed" in titles
    assert "Citadel Siege" in titles
    assert "Fall of Malakar" not in titles

    # Malakar should still be alive at scene 2.0
    assert state.is_character_alive(seeded_project["malakar"].id) is True

    # Narrative thread should be open
    assert len(state.open_threads) == 1
    assert state.open_threads[0].title == "Who Betrayed the Citadel?"


@pytest.mark.asyncio
async def test_narrative_state_after_malakar_death(test_session: AsyncSession, seeded_project):
    """Verify story state snapshot at narrative position 3.5 (after Malakar dies)."""
    proj = seeded_project["project"]
    state = await get_story_state(test_session, proj.id, narrative_position=3.5)

    assert len(state.established_events) == 3
    # Malakar is now dead based on scene 3.0 metadata
    assert state.is_character_alive(seeded_project["malakar"].id) is False
    # Elena is still alive
    assert state.is_character_alive(seeded_project["elena"].id) is True

    # Narrative thread is still open (resolves at 4.0)
    assert len(state.open_threads) == 1


@pytest.mark.asyncio
async def test_narrative_thread_resolution(test_session: AsyncSession, seeded_project):
    """Verify narrative thread is considered closed after resolution position 4.0."""
    proj = seeded_project["project"]
    # At narrative position 4.5, thread resolved at 4.0 should no longer be in open_threads
    state = await get_story_state(test_session, proj.id, narrative_position=4.5)
    assert len(state.open_threads) == 0


@pytest.mark.asyncio
async def test_decoupling_narrative_and_chronological_order(
    test_session: AsyncSession, seeded_project
):
    """Verify chronological ordering differs from narrative ordering when flashbacks exist."""
    proj = seeded_project["project"]
    state = await get_story_state(test_session, proj.id, narrative_position=4.0)

    # Chronological sort should place e1 (order=10.0) first, e2 (50.0), e3 (60.0), e4 (70.0)
    chrono_events = state.chronological_events
    orders = [e.chronological_order for e in chrono_events]
    assert orders == [10.0, 50.0, 60.0, 70.0]
