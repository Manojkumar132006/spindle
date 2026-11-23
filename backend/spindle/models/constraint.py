"""Constraint model representing author-defined narrative boundaries."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spindle.models.base import (
    ConstraintSeverity,
    ConstraintType,
    EnforcementMethod,
    UUIDBaseModel,
)

if TYPE_CHECKING:
    from spindle.models.project import Project


class Constraint(UUIDBaseModel):
    """Author-defined or world-derived narrative boundary enforced during story generation."""

    __tablename__ = "constraints"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    constraint_type: Mapped[str] = mapped_column(
        String(50),
        default=ConstraintType.CANON.value,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        default=ConstraintSeverity.HARD.value,
        nullable=False,
    )
    enforcement_method: Mapped[str] = mapped_column(
        String(50),
        default=EnforcementMethod.DETERMINISTIC.value,
        nullable=False,
    )
    scope: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="constraints")
