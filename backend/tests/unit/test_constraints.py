"""Unit tests for Centralized Constraint Engine & Deterministic Validators (Task 3.3)."""

import uuid

import pytest

from spindle.core.constraints.deterministic.chronology import ChronologyValidator
from spindle.core.constraints.deterministic.entity_existence import EntityExistenceValidator
from spindle.core.constraints.deterministic.epistemic import EpistemicValidator
from spindle.core.constraints.deterministic.life_status import LifeStatusValidator
from spindle.core.constraints.deterministic.world_rule import WorldRuleValidator
from spindle.core.constraints.engine import ConstraintEngine
from spindle.core.constraints.report import ValidationOutcome
from spindle.core.state_service import StoryState
from spindle.models.base import EnforcementLevel, KnowledgeStatus, RuleType
from spindle.models.constraint import Constraint
from spindle.models.entity import Character, WorldRule
from spindle.models.event import Event
from spindle.models.knowledge import CharacterKnowledge


@pytest.fixture
def mock_story_state():
    """Create in-memory StoryState for deterministic validation tests."""
    proj_id = uuid.uuid4()
    c1_id = uuid.uuid4()
    c2_id = uuid.uuid4()

    c1 = Character(id=c1_id, project_id=proj_id, name="Arya", current_state="alive")
    c2 = Character(id=c2_id, project_id=proj_id, name="Ned Stark", current_state="deceased")

    e1 = Event(
        id=uuid.uuid4(),
        project_id=proj_id,
        title="Tourney at Harrenhal",
        narrative_position=1.0,
        chronological_order=10.0,
    )
    e2 = Event(
        id=uuid.uuid4(),
        project_id=proj_id,
        title="Execution at the Sept",
        narrative_position=3.0,
        chronological_order=20.0,
    )

    k1 = CharacterKnowledge(
        character_id=c1_id,
        fact_or_event_id="SecretTunnel",
        knowledge_status=KnowledgeStatus.CONFIRMED.value,
        acquired_at=2.0,
    )

    rule1 = WorldRule(
        project_id=proj_id,
        name="No Resurrection Magic",
        description="In this universe, resurrection is impossible and no one returns from death.",
        rule_type=RuleType.MAGIC.value,
        enforcement_level=EnforcementLevel.HARD.value,
        metadata_json={"forbidden_triggers": ["instant teleportation"]},
    )

    constraint1 = Constraint(
        project_id=proj_id,
        name="Strict Weapon Canon",
        description="Valyrian steel cannot be melted by normal fire",
        active=True,
        severity=EnforcementLevel.HARD.value,
        parameters={"prohibited_actions": ["melts needle with candle"]},
    )

    return StoryState(
        project_id=proj_id,
        narrative_position=4.0,
        characters=[c1, c2],
        established_events=[e1, e2],
        active_world_rules=[rule1],
        active_constraints=[constraint1],
        character_knowledge={c1_id: [k1]},
    )


@pytest.mark.asyncio
async def test_chronology_validator_preconditions(mock_story_state):
    validator = ChronologyValidator()

    # 1. Valid precondition established in the past
    valid_proposal = {
        "narrative_position": 4.0,
        "chronological_order": 25.0,
        "causal_dependencies": ["Tourney at Harrenhal"],
    }
    diags = await validator.validate(valid_proposal, mock_story_state)
    assert all(d.outcome == ValidationOutcome.PASS for d in diags)

    # 2. Missing precondition
    missing_proposal = {
        "narrative_position": 4.0,
        "causal_dependencies": ["NonExistentWar"],
    }
    diags_missing = await validator.validate(missing_proposal, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_missing)
    assert "Unresolved Causal Precondition" in diags_missing[0].rule_name

    # 3. Chronological paradox (precondition occurs at 20.0, proposed event claims 15.0)
    paradox_proposal = {
        "narrative_position": 4.0,
        "chronological_order": 15.0,
        "causal_dependencies": ["Execution at the Sept"],
    }
    diags_paradox = await validator.validate(paradox_proposal, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_paradox)
    assert "Temporal Causality Paradox" in diags_paradox[0].rule_name


@pytest.mark.asyncio
async def test_life_status_validator(mock_story_state):
    validator = LifeStatusValidator()

    # 1. Alive character participating
    alive_proposal = {
        "participants": ["Arya"],
        "scene_type": "duel",
    }
    diags_alive = await validator.validate(alive_proposal, mock_story_state)
    assert all(d.outcome == ValidationOutcome.PASS for d in diags_alive)

    # 2. Deceased character actively participating without flashback
    dead_proposal = {
        "participants": ["Ned Stark"],
        "scene_type": "standard",
    }
    diags_dead = await validator.validate(dead_proposal, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_dead)
    assert "Deceased Character Physical Availability" in diags_dead[0].rule_name

    # 3. Deceased character in flashback scene -> Allowed
    flashback_proposal = {
        "participants": ["Ned Stark"],
        "scene_type": "flashback",
    }
    diags_flashback = await validator.validate(flashback_proposal, mock_story_state)
    assert all(d.outcome == ValidationOutcome.PASS for d in diags_flashback)


@pytest.mark.asyncio
async def test_epistemic_validator(mock_story_state):
    validator = EpistemicValidator()

    # 1. Arya acting on known secret (learned at 2.0, proposal at 4.0)
    valid_epistemic = {
        "narrative_position": 4.0,
        "required_knowledge": [{"character": "Arya", "fact": "SecretTunnel"}],
    }
    diags = await validator.validate(valid_epistemic, mock_story_state)
    assert all(d.outcome == ValidationOutcome.PASS for d in diags)

    # 2. Arya acting on unearned secret
    invalid_epistemic = {
        "narrative_position": 4.0,
        "required_knowledge": [{"character": "Arya", "fact": "PoisonerIdentity"}],
    }
    diags_invalid = await validator.validate(invalid_epistemic, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_invalid)
    assert "Unearned Epistemic Access" in diags_invalid[0].rule_name


@pytest.mark.asyncio
async def test_world_rule_validator(mock_story_state):
    validator = WorldRuleValidator()

    # 1. Action violating magic resurrection law
    resurrection_proposal = {
        "title": "Reviving Ned",
        "premise": "A wizard performs a spell to resurrect the fallen hero.",
    }
    diags_res = await validator.validate(resurrection_proposal, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_res)
    assert "Absolute Magic Law" in diags_res[0].rule_name

    # 2. Action violating forbidden trigger in rule metadata
    trigger_proposal = {
        "premise": "They used instant teleportation to reach the castle.",
    }
    diags_trigger = await validator.validate(trigger_proposal, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_trigger)

    # 3. Action violating author constraint
    constraint_proposal = {
        "premise": "In frustration, she melts needle with candle flame.",
    }
    diags_c = await validator.validate(constraint_proposal, mock_story_state)
    assert any(d.outcome == ValidationOutcome.FAIL for d in diags_c)


@pytest.mark.asyncio
async def test_centralized_constraint_engine(mock_story_state):
    engine = ConstraintEngine()

    # A proposal with multiple violations: deceased character + unlearned knowledge
    violating_proposal = {
        "narrative_position": 4.0,
        "participants": ["Ned Stark"],
        "required_knowledge": [{"character": "Arya", "fact": "HiddenAssassin"}],
        "causal_dependencies": ["NonExistentBattle"],
    }
    report = await engine.validate(violating_proposal, mock_story_state)

    assert report.overall_outcome == ValidationOutcome.FAIL
    assert report.is_valid is False
    assert report.has_hard_failures is True
    assert report.failed_count >= 3
    assert "Validation FAILED" in report.summary

    # Valid proposal
    valid_proposal = {
        "narrative_position": 4.0,
        "participants": ["Arya"],
        "required_knowledge": [{"character": "Arya", "fact": "SecretTunnel"}],
        "causal_dependencies": ["Tourney at Harrenhal"],
    }
    valid_report = await engine.validate(valid_proposal, mock_story_state)
    assert valid_report.overall_outcome == ValidationOutcome.PASS
    assert valid_report.is_valid is True


@pytest.mark.asyncio
async def test_entity_existence_validator(mock_story_state):
    validator = EntityExistenceValidator()

    # 1. Valid: Established character
    valid_res = await validator.validate({"involved_characters": ["Arya"]}, mock_story_state)
    assert len(valid_res) == 0

    # 2. Valid: Allowed generic extra / role
    extra_res = await validator.validate(
        {"involved_characters": ["Arya", "the station conductor", "city guard"]},
        mock_story_state,
    )
    assert len(extra_res) == 0

    # 3. Invalid: Nonexistent named character
    invalid_res = await validator.validate(
        {"involved_characters": ["Arya", "Aldric Voss", "Garrick"]},
        mock_story_state,
    )
    assert len(invalid_res) == 2
    assert invalid_res[0].outcome == ValidationOutcome.FAIL
    assert "Aldric Voss" in invalid_res[0].message
    assert "Garrick" in invalid_res[1].message
