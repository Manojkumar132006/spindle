"""CharacterKnowledge model representing character epistemic state."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spindle.models.base import KnowledgeStatus, UUIDBaseModel

if TYPE_CHECKING:
    from spindle.models.entity import Character
    from spindle.models.event import Event


class CharacterKnowledge(UUIDBaseModel):
    """Epistemic ledger recording what a character knows, suspects, or believes."""

    __tablename__ = "character_knowledge"

    character_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fact_or_event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    knowledge_status: Mapped[str] = mapped_column(
        String(50),
        default=KnowledgeStatus.CONFIRMED.value,
        nullable=False,
    )
    acquired_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    acquired_chronological: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="knowledge_items")
    source_event: Mapped["Event | None"] = relationship("Event")
