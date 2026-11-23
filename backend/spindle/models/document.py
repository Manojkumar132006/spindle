"""SourceDocument and DocumentExcerpt models for vault file tracking and provenance."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spindle.models.base import DocumentType, UUIDBaseModel

if TYPE_CHECKING:
    from spindle.models.project import Project


class SourceDocument(UUIDBaseModel):
    """Represents an ingested Markdown file from the author's Obsidian vault."""

    __tablename__ = "source_documents"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50),
        default=DocumentType.GENERAL.value,
        nullable=False,
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("project_id", "file_path", name="uq_project_file_path"),)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="source_documents")
    excerpts: Mapped[list["DocumentExcerpt"]] = relationship(
        "DocumentExcerpt",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentExcerpt(UUIDBaseModel):
    """Passages or section excerpts with semantic embeddings for hybrid retrieval."""

    __tablename__ = "document_excerpts"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    excerpt_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    document: Mapped["SourceDocument"] = relationship("SourceDocument", back_populates="excerpts")
