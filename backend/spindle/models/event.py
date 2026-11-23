"""Event and NarrativeThread models for tracking narrative sequence, causality, and arcs."""

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

from spindle.models.base import CanonStatus, ThreadStatus, UUIDBaseModel

if TYPE_CHECKING:
    from spindle.models.document import SourceDocument
    from spindle.models.entity import Location
    from spindle.models.project import Project


class Event(UUIDBaseModel):
    """Narrative or historical event tracking story placement and chronological timestamp."""

    __tablename__ = "events"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_position: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )
    chronological_timestamp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chronological_order: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    participants: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    causal_dependencies: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    canon_status: Mapped[str] = mapped_column(
        String(50),
        default=CanonStatus.CONFIRMED.value,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="events")
    location: Mapped["Location | None"] = relationship("Location")
    source_document: Mapped["SourceDocument | None"] = relationship("SourceDocument")


class NarrativeThread(UUIDBaseModel):
    """Unresolved narrative threads, plot questions, and overarching story arcs."""

    __tablename__ = "narrative_threads"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    involved_entities: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    introduction_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolution_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=ThreadStatus.OPEN.value,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="narrative_threads")
    introduction_event: Mapped["Event | None"] = relationship(
        "Event",
        foreign_keys=[introduction_event_id],
    )
    resolution_event: Mapped["Event | None"] = relationship(
        "Event",
        foreign_keys=[resolution_event_id],
    )
