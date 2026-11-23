"""Character Epistemic (Knowledge) Ledger query and verification service."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spindle.models.base import KnowledgeStatus
from spindle.models.knowledge import CharacterKnowledge


@dataclass
class EpistemicAccessResult:
    """Outcome of validating a character's epistemic access to a fact at a story position."""

    allowed: bool
    character_id: uuid.UUID
    fact_or_event_id: str
    current_status: KnowledgeStatus
    acquired_at: float | None
    requested_at: float
    leakage_detected: bool
    reason: str


class EpistemicLedgerService:
    """Service for managing and querying character knowledge states over narrative time."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_character_knowledge_items(
        self,
        character_id: uuid.UUID,
        narrative_position: float,
        fact_or_event_id: str | None = None,
    ) -> list[CharacterKnowledge]:
        """Query knowledge items acquired by a character at or prior to narrative_position."""
        stmt = (
            select(CharacterKnowledge)
            .options(selectinload(CharacterKnowledge.source_event))
            .where(CharacterKnowledge.character_id == character_id)
            .order_by(CharacterKnowledge.acquired_at.asc(), CharacterKnowledge.created_at.asc())
        )
        if fact_or_event_id:
            stmt = stmt.where(CharacterKnowledge.fact_or_event_id == fact_or_event_id)

        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        valid_items: list[CharacterKnowledge] = []
        for item in items:
            acq = item.acquired_at
            if acq is None and item.source_event:
                acq = item.source_event.narrative_position
            if acq is None:
                acq = 0.0

            if acq <= narrative_position:
                valid_items.append(item)

        return valid_items

    async def get_epistemic_status(
        self,
        character_id: uuid.UUID,
        fact_or_event_id: str,
        narrative_position: float,
    ) -> KnowledgeStatus:
        """Return the effective epistemic status of a character regarding a fact at narrative_position."""
        items = await self.get_character_knowledge_items(
            character_id=character_id,
            narrative_position=narrative_position,
            fact_or_event_id=fact_or_event_id,
        )

        if not items:
            return KnowledgeStatus.UNKNOWN

        # Return the latest transition status acquired at or before this position
        latest_item = items[-1]
        try:
            return KnowledgeStatus(latest_item.knowledge_status)
        except ValueError:
            return KnowledgeStatus.CONFIRMED

    async def validate_knowledge_access(
        self,
        character_id: uuid.UUID,
        fact_or_event_id: str,
        at_narrative_position: float,
        required_status: set[KnowledgeStatus] | None = None,
    ) -> EpistemicAccessResult:
        """Check whether character legitimately holds the required knowledge status at the requested scene position."""
        if required_status is None:
            required_status = {
                KnowledgeStatus.BELIEVED,
                KnowledgeStatus.CONFIRMED,
            }

        # Check future knowledge to see if leakage occurs (i.e. fact is learned later)
        all_stmt = (
            select(CharacterKnowledge)
            .options(selectinload(CharacterKnowledge.source_event))
            .where(
                CharacterKnowledge.character_id == character_id,
                CharacterKnowledge.fact_or_event_id == fact_or_event_id,
            )
            .order_by(CharacterKnowledge.acquired_at.asc())
        )
        res = await self.session.execute(all_stmt)
        all_items = list(res.scalars().all())

        # Determine effective status up to requested position
        prior_items = []
        future_items = []
        for item in all_items:
            acq = item.acquired_at
            if acq is None and item.source_event:
                acq = item.source_event.narrative_position
            if acq is None:
                acq = 0.0

            if acq <= at_narrative_position:
                prior_items.append((acq, item))
            else:
                future_items.append((acq, item))

        if not prior_items:
            current_status = KnowledgeStatus.UNKNOWN
            acquired_at = None
        else:
            last_acq, last_item = prior_items[-1]
            try:
                current_status = KnowledgeStatus(last_item.knowledge_status)
            except ValueError:
                current_status = KnowledgeStatus.CONFIRMED
            acquired_at = last_acq

        # Check if fact is only learned in the future (anachronistic leakage)
        if current_status not in required_status and future_items:
            future_acq, _ = future_items[0]
            return EpistemicAccessResult(
                allowed=False,
                character_id=character_id,
                fact_or_event_id=fact_or_event_id,
                current_status=current_status,
                acquired_at=future_acq,
                requested_at=at_narrative_position,
                leakage_detected=True,
                reason=(
                    f"Anachronistic knowledge leakage: Character does not learn '{fact_or_event_id}' "
                    f"until narrative position {future_acq}, but attempted access at {at_narrative_position}."
                ),
            )

        if current_status not in required_status:
            return EpistemicAccessResult(
                allowed=False,
                character_id=character_id,
                fact_or_event_id=fact_or_event_id,
                current_status=current_status,
                acquired_at=acquired_at,
                requested_at=at_narrative_position,
                leakage_detected=False,
                reason=(
                    f"Epistemic restriction: Character holds status '{current_status.value}' for "
                    f"'{fact_or_event_id}', which does not satisfy required status "
                    f"{[s.value for s in required_status]}."
                ),
            )

        return EpistemicAccessResult(
            allowed=True,
            character_id=character_id,
            fact_or_event_id=fact_or_event_id,
            current_status=current_status,
            acquired_at=acquired_at,
            requested_at=at_narrative_position,
            leakage_detected=False,
            reason=f"Character legitimately holds status '{current_status.value}' at position {at_narrative_position}.",
        )

    async def record_knowledge_transition(
        self,
        character_id: uuid.UUID,
        fact_or_event_id: str,
        new_status: KnowledgeStatus,
        narrative_position: float,
        chronological_order: float | None = None,
        source_event_id: uuid.UUID | None = None,
        details: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CharacterKnowledge:
        """Record an epistemic status transition in the ledger."""
        item = CharacterKnowledge(
            character_id=character_id,
            fact_or_event_id=fact_or_event_id,
            knowledge_status=new_status.value,
            acquired_at=narrative_position,
            acquired_chronological=chronological_order,
            source_event_id=source_event_id,
            details=details,
            metadata_json=metadata_json or {},
        )
        self.session.add(item)
        await self.session.flush()
        return item
