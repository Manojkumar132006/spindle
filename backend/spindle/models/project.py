"""Project model representing isolated fictional universes or stories."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spindle.models.base import UUIDBaseModel

if TYPE_CHECKING:
    from spindle.models.constraint import Constraint
    from spindle.models.document import SourceDocument
    from spindle.models.entity import Character, Location, Relationship, WorldRule
    from spindle.models.event import Event, NarrativeThread
    from spindle.models.suggestion import NarrativeBranch, Suggestion


class Project(UUIDBaseModel):
    """Isolated project workspace representing an author's fictional universe."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        "SourceDocument",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    characters: Mapped[list["Character"]] = relationship(
        "Character",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    locations: Mapped[list["Location"]] = relationship(
        "Location",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    world_rules: Mapped[list["WorldRule"]] = relationship(
        "WorldRule",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    relationships: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    narrative_threads: Mapped[list["NarrativeThread"]] = relationship(
        "NarrativeThread",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    constraints: Mapped[list["Constraint"]] = relationship(
        "Constraint",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    narrative_branches: Mapped[list["NarrativeBranch"]] = relationship(
        "NarrativeBranch",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        "Suggestion",
        back_populates="project",
        cascade="all, delete-orphan",
    )

