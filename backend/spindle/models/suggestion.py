"""Suggestion, SuggestionRevision, and NarrativeBranch models for creative generation."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spindle.models.base import (
    ApprovalStatus,
    BranchStatus,
    BranchType,
    SuggestionType,
    UUIDBaseModel,
)

if TYPE_CHECKING:
    from spindle.models.project import Project


class NarrativeBranch(UUIDBaseModel):
    """Narrative branch supporting what-if hypotheses and isolated story branches."""

    __tablename__ = "narrative_branches"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("narrative_branches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    branch_type: Mapped[str] = mapped_column(
        String(50),
        default=BranchType.MAIN.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=BranchStatus.ACTIVE.value,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="narrative_branches")
    suggestions: Mapped[list["Suggestion"]] = relationship(
        "Suggestion",
        back_populates="branch",
    )


class Suggestion(UUIDBaseModel):
    """Generated creative proposal (plot point, side story, or continuity report)."""

    __tablename__ = "suggestions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggestion_type: Mapped[str] = mapped_column(
        String(50),
        default=SuggestionType.PLOT_POINT.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    premise: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    supporting_evidence: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    assumptions: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    validation_results: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("narrative_branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_status: Mapped[str] = mapped_column(
        String(50),
        default=ApprovalStatus.GENERATED.value,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_edits: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="suggestions")
    branch: Mapped["NarrativeBranch | None"] = relationship(
        "NarrativeBranch",
        back_populates="suggestions",
    )
    revisions: Mapped[list["SuggestionRevision"]] = relationship(
        "SuggestionRevision",
        back_populates="suggestion",
        cascade="all, delete-orphan",
    )


class SuggestionRevision(UUIDBaseModel):
    """Historical revision log of a suggestion across LangGraph iteration loops or author edits."""

    __tablename__ = "suggestion_revisions"

    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suggestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    validation_results: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    revision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    suggestion: Mapped["Suggestion"] = relationship("Suggestion", back_populates="revisions")

