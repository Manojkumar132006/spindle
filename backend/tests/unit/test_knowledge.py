"""Unit tests for the Character Epistemic Ledger (Task 3.2)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.core.knowledge import EpistemicLedgerService
from spindle.models.base import KnowledgeStatus
from spindle.models.entity import Character
from spindle.models.project import Project


@pytest.fixture
async def epistemic_setup(test_session: AsyncSession):
    proj = Project(name="Epistemic Universe")
    test_session.add(proj)
    await test_session.flush()

    c1 = Character(project_id=proj.id, name="Detective Miller")
    test_session.add(c1)
    await test_session.flush()

    service = EpistemicLedgerService(test_session)
    return {"service": service, "character": c1, "project": proj}


@pytest.mark.asyncio
async def test_epistemic_status_transitions(test_session: AsyncSession, epistemic_setup):
    service: EpistemicLedgerService = epistemic_setup["service"]
    char = epistemic_setup["character"]
    fact = "CulpritIdentity"

    # Before any acquisition: status must be UNKNOWN
    status_0 = await service.get_epistemic_status(char.id, fact, narrative_position=1.0)
    assert status_0 == KnowledgeStatus.UNKNOWN

    # At scene 2.0, Miller suspects the butler
    await service.record_knowledge_transition(
        character_id=char.id,
        fact_or_event_id=fact,
        new_status=KnowledgeStatus.SUSPECTED,
        narrative_position=2.0,
        details="Noticed muddy footprints near the library",
    )

    # At scene 5.0, Miller confirms the butler did it
    await service.record_knowledge_transition(
        character_id=char.id,
        fact_or_event_id=fact,
        new_status=KnowledgeStatus.CONFIRMED,
        narrative_position=5.0,
        details="Found the poisoned letter in butler's coat",
    )

    # Query status at scene 1.5 -> UNKNOWN
    assert await service.get_epistemic_status(char.id, fact, 1.5) == KnowledgeStatus.UNKNOWN
    # Query status at scene 3.0 -> SUSPECTED
    assert await service.get_epistemic_status(char.id, fact, 3.0) == KnowledgeStatus.SUSPECTED
    # Query status at scene 5.0+ -> CONFIRMED
    assert await service.get_epistemic_status(char.id, fact, 5.0) == KnowledgeStatus.CONFIRMED


@pytest.mark.asyncio
async def test_prevent_anachronistic_knowledge_leakage(test_session: AsyncSession, epistemic_setup):
    service: EpistemicLedgerService = epistemic_setup["service"]
    char = epistemic_setup["character"]
    fact = "SecretPassageway"

    # Secret is learned at narrative position 8.0
    await service.record_knowledge_transition(
        character_id=char.id,
        fact_or_event_id=fact,
        new_status=KnowledgeStatus.CONFIRMED,
        narrative_position=8.0,
        details="Discovered switch behind the portrait",
    )

    # Attempting to access/act on this secret at narrative position 3.0
    result = await service.validate_knowledge_access(
        character_id=char.id,
        fact_or_event_id=fact,
        at_narrative_position=3.0,
    )

    assert result.allowed is False
    assert result.leakage_detected is True
    assert result.acquired_at == 8.0
    assert result.requested_at == 3.0
    assert "Anachronistic knowledge leakage" in result.reason


@pytest.mark.asyncio
async def test_valid_epistemic_access(test_session: AsyncSession, epistemic_setup):
    service: EpistemicLedgerService = epistemic_setup["service"]
    char = epistemic_setup["character"]
    fact = "KingIsSick"

    await service.record_knowledge_transition(
        character_id=char.id,
        fact_or_event_id=fact,
        new_status=KnowledgeStatus.CONFIRMED,
        narrative_position=2.0,
    )

    # Access at position 2.5 is legitimate
    result = await service.validate_knowledge_access(
        character_id=char.id,
        fact_or_event_id=fact,
        at_narrative_position=2.5,
    )
    assert result.allowed is True
    assert result.leakage_detected is False
