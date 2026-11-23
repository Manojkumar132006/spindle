"""Vault synchronization endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.api.deps import get_current_project
from spindle.api.v1.schemas import (
    VaultStatusResponse,
    VaultSyncRequest,
    VaultSyncResponse,
)
from spindle.database import get_db_session
from spindle.ingestion.sync import VaultSyncEngine
from spindle.models.document import SourceDocument
from spindle.models.project import Project

router = APIRouter(prefix="/vault", tags=["Vault"])


@router.post(
    "/sync",
    response_model=VaultSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Obsidian vault files",
)
async def sync_vault(
    payload: VaultSyncRequest,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VaultSyncResponse:
    """Synchronize a batch of Markdown vault files into the narrative state database.

    Calculates content hashes, updates modified files, indexes new files,
    and resolves extracted characters, events, locations, and world rules.
    """
    file_map = {f.path: f.content for f in payload.files}
    engine = VaultSyncEngine(session=session, project_id=project.id)
    result = await engine.sync_vault(file_map)

    return VaultSyncResponse(
        status="success" if not result.errors else "partial_success",
        project_id=project.id,
        total_files=result.total_files,
        indexed_files=result.indexed_files,
        updated_files=result.updated_files,
        skipped_files=result.skipped_files,
        deleted_files=result.deleted_files,
        extracted_characters=result.extracted_characters,
        extracted_events=result.extracted_events,
        extracted_locations=result.extracted_locations,
        extracted_rules=result.extracted_rules,
        extracted_excerpts=result.extracted_excerpts,
        errors=result.errors,
        synced_at=result.synced_at,
    )


@router.get(
    "/status",
    response_model=VaultStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get vault synchronization status",
)
async def get_vault_status(
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VaultStatusResponse:
    """Retrieve synchronization metrics and last indexed timestamp."""
    count_stmt = select(func.count(SourceDocument.id)).where(
        SourceDocument.project_id == project.id
    )
    doc_count = (await session.execute(count_stmt)).scalar() or 0

    latest_stmt = (
        select(SourceDocument.indexed_at)
        .where(SourceDocument.project_id == project.id)
        .order_by(SourceDocument.indexed_at.desc())
        .limit(1)
    )
    last_synced = (await session.execute(latest_stmt)).scalar_one_or_none()

    return VaultStatusResponse(
        project_id=project.id,
        project_name=project.name,
        total_documents=doc_count,
        last_synced_at=last_synced,
        is_syncing=False,
    )
