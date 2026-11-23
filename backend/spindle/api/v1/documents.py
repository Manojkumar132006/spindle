"""Source document query endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spindle.api.deps import get_current_project
from spindle.api.v1.schemas import DocumentSummary
from spindle.database import get_db_session
from spindle.models.document import SourceDocument
from spindle.models.project import Project

router = APIRouter(prefix="/documents", tags=["Documents"])


class ExcerptItem(BaseModel):
    """An excerpt entry belonging to a source document."""

    id: uuid.UUID
    excerpt_text: str
    heading: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]


class DocumentDetailResponse(BaseModel):
    """Detailed view of an indexed document with provenance excerpts."""

    id: uuid.UUID
    project_id: uuid.UUID
    file_path: str
    content_hash: str
    document_type: str
    raw_content: str
    parsed_metadata: dict[str, Any]
    excerpts: list[ExcerptItem]


@router.get(
    "",
    response_model=list[DocumentSummary],
    status_code=status.HTTP_200_OK,
    summary="List all indexed source documents",
)
async def list_documents(
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DocumentSummary]:
    """Retrieve indexed documents for the project."""
    stmt = (
        select(SourceDocument)
        .where(SourceDocument.project_id == project.id)
        .order_by(SourceDocument.file_path.asc())
    )
    docs = (await session.execute(stmt)).scalars().all()
    return [
        DocumentSummary(
            id=d.id,
            file_path=d.file_path,
            content_hash=d.content_hash,
            document_type=d.document_type,
            indexed_at=d.indexed_at,
        )
        for d in docs
    ]


@router.get(
    "/{doc_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific source document",
)
async def get_document(
    doc_id: uuid.UUID,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentDetailResponse:
    """Retrieve full raw content and section excerpts for a source document."""
    stmt = (
        select(SourceDocument)
        .options(selectinload(SourceDocument.excerpts))
        .where(SourceDocument.id == doc_id, SourceDocument.project_id == project.id)
    )
    doc = (await session.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    excerpt_items = [
        ExcerptItem(
            id=e.id,
            excerpt_text=e.excerpt_text,
            heading=e.heading,
            start_line=e.start_line,
            end_line=e.end_line,
            metadata=e.metadata_json,
        )
        for e in doc.excerpts
    ]

    return DocumentDetailResponse(
        id=doc.id,
        project_id=doc.project_id,
        file_path=doc.file_path,
        content_hash=doc.content_hash,
        document_type=doc.document_type,
        raw_content=doc.raw_content,
        parsed_metadata=doc.parsed_metadata,
        excerpts=excerpt_items,
    )
