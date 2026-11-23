"""Pydantic schemas for API request and response validation."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class SyncFilePayload(BaseModel):
    """A file payload submitted for vault synchronization."""

    path: str = Field(
        validation_alias=AliasChoices("path", "file_path"),
        description="Relative vault file path, e.g. Characters/Elena.md",
    )
    content: str = Field(description="Raw markdown prose including YAML frontmatter")


class VaultSyncRequest(BaseModel):
    """Payload for batch vault synchronization."""

    files: list[SyncFilePayload] = Field(description="List of files to synchronize")
    project_id: uuid.UUID | None = Field(default=None, description="Optional target project ID")


class VaultSyncResponse(BaseModel):
    """Response returned after vault synchronization."""

    status: str
    project_id: uuid.UUID
    total_files: int
    indexed_files: int
    updated_files: int
    skipped_files: int
    deleted_files: int
    extracted_characters: int
    extracted_events: int
    extracted_locations: int
    extracted_rules: int
    extracted_excerpts: int
    errors: list[str]
    synced_at: datetime


class VaultStatusResponse(BaseModel):
    """Current synchronization state of the vault."""

    project_id: uuid.UUID
    project_name: str
    total_documents: int
    last_synced_at: datetime | None
    is_syncing: bool = False


class StoryOverviewResponse(BaseModel):
    """High-level summary metrics of the author's narrative universe."""

    project_id: uuid.UUID
    project_name: str
    description: str | None = None
    characters_count: int
    events_count: int
    locations_count: int
    world_rules_count: int
    constraints_count: int
    open_threads_count: int
    documents_count: int
    last_synced_at: datetime | None


class EntitySummary(BaseModel):
    """Normalized summary of a story entity."""

    id: uuid.UUID
    name: str
    entity_type: str
    role_or_kind: str | None = None
    description: str | None = None
    canon_status: str | None = None
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntitiesListResponse(BaseModel):
    """Collection of extracted narrative entities."""

    project_id: uuid.UUID
    characters: list[EntitySummary]
    events: list[EntitySummary]
    locations: list[EntitySummary]
    world_rules: list[EntitySummary]


class DocumentSummary(BaseModel):
    """Summary of an indexed source document."""

    id: uuid.UUID
    file_path: str
    content_hash: str
    document_type: str
    indexed_at: datetime
