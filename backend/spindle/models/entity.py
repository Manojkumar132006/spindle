"""Character, Location, WorldRule, and Relationship narrative entity models."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spindle.models.base import CanonStatus, EnforcementLevel, RuleType, UUIDBaseModel

if TYPE_CHECKING:
    from spindle.models.knowledge import CharacterKnowledge
    from spindle.models.project import Project


class Character(UUIDBaseModel):
    """Normalized character entity tracking psychological profile and current state."""

    __tablename__ = "characters"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivations: Mapped[str | None] = mapped_column(Text, nullable=True)
    fears: Mapped[str | None] = mapped_column(Text, nullable=True)
    secrets: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_state: Mapped[str | None] = mapped_column(String(100), default="alive", nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    canon_status: Mapped[str] = mapped_column(
        String(50),
        default=CanonStatus.EXTRACTED.value,
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    knowledge_items: Mapped[list["CharacterKnowledge"]] = relationship(
        "CharacterKnowledge",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    relationships_as_source: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.source_character_id",
        back_populates="source_character",
        cascade="all, delete-orphan",
    )
    relationships_as_target: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.target_character_id",
        back_populates="target_character",
        cascade="all, delete-orphan",
    )


class Location(UUIDBaseModel):
    """Worldbuilding location or setting."""

    __tablename__ = "locations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kind: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="locations")


class WorldRule(UUIDBaseModel):
    """Rules governing magic, cosmology, society, physics, or world constraints."""

    __tablename__ = "world_rules"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(
        String(50),
        default=RuleType.GENERAL.value,
        nullable=False,
    )
    enforcement_level: Mapped[str] = mapped_column(
        String(50),
        default=EnforcementLevel.HARD.value,
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="world_rules")


class Relationship(UUIDBaseModel):
    """Directed connection or bond between two characters."""

    __tablename__ = "relationships"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_character_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_character_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    current_state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    history: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="relationships")
    source_character: Mapped["Character"] = relationship(
        "Character",
        foreign_keys=[source_character_id],
        back_populates="relationships_as_source",
    )
    target_character: Mapped["Character"] = relationship(
        "Character",
        foreign_keys=[target_character_id],
        back_populates="relationships_as_target",
    )
