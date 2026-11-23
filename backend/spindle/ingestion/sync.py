"""Incremental vault synchronization engine coordinating hashing, parsing, and persistence."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.ingestion.extractor import extract_from_document
from spindle.ingestion.hasher import FileChangeStatus, detect_file_changes
from spindle.ingestion.parser import parse_markdown
from spindle.ingestion.resolver import EntityResolver
from spindle.models.document import DocumentExcerpt, SourceDocument
from spindle.models.entity import Character, Location, WorldRule
from spindle.models.event import Event


@dataclass
class SyncResult:
    """Summary metrics of an executed vault synchronization."""

    project_id: uuid.UUID
    total_files: int = 0
    indexed_files: int = 0
    updated_files: int = 0
    skipped_files: int = 0
    deleted_files: int = 0
    extracted_characters: int = 0
    extracted_events: int = 0
    extracted_locations: int = 0
    extracted_rules: int = 0
    extracted_excerpts: int = 0
    errors: list[str] = field(default_factory=list)
    synced_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class VaultSyncEngine:
    """Orchestrates incremental vault indexing, change detection, and persistence."""

    def __init__(self, session: AsyncSession, project_id: uuid.UUID):
        self.session = session
        self.project_id = project_id
        self.resolver = EntityResolver(project_id)

    async def _preload_existing_entities(self) -> None:
        """Preload existing characters, locations, events, and rules into the resolver."""
        # Characters
        char_stmt = select(Character).where(Character.project_id == self.project_id)
        chars = (await self.session.execute(char_stmt)).scalars().all()
        for c in chars:
            self.resolver.register(c.id, c.name, "character", c.aliases)

        # Locations
        loc_stmt = select(Location).where(Location.project_id == self.project_id)
        locs = (await self.session.execute(loc_stmt)).scalars().all()
        for loc in locs:
            self.resolver.register(loc.id, loc.name, "location")

        # Events
        evt_stmt = select(Event).where(Event.project_id == self.project_id)
        events = (await self.session.execute(evt_stmt)).scalars().all()
        for e in events:
            self.resolver.register(e.id, e.title, "event")

        # World Rules
        rule_stmt = select(WorldRule).where(WorldRule.project_id == self.project_id)
        rules = (await self.session.execute(rule_stmt)).scalars().all()
        for r in rules:
            self.resolver.register(r.id, r.name, "world_rule")

    async def sync_vault(self, files: dict[str, str]) -> SyncResult:
        """Execute incremental synchronization on incoming vault files."""
        result = SyncResult(project_id=self.project_id, total_files=len(files))

        await self._preload_existing_entities()

        # Query existing documents
        doc_stmt = select(SourceDocument).where(SourceDocument.project_id == self.project_id)
        existing_docs = (await self.session.execute(doc_stmt)).scalars().all()
        existing_map = {doc.file_path: doc for doc in existing_docs}
        existing_hashes = {doc.file_path: doc.content_hash for doc in existing_docs}

        # Detect changes
        changes = detect_file_changes(existing_hashes, files)

        for file_path, (change_status, content_hash) in changes.items():
            try:
                # 1. Unmodified files: skip
                if change_status == FileChangeStatus.UNMODIFIED:
                    result.skipped_files += 1
                    continue

                # 2. Deleted files: remove document
                if change_status == FileChangeStatus.DELETED:
                    doc_to_delete = existing_map.get(file_path)
                    if doc_to_delete:
                        await self.session.delete(doc_to_delete)
                        result.deleted_files += 1
                    continue

                # 3. New or Modified files: parse and extract
                raw_content = files[file_path]
                parsed = parse_markdown(raw_content, file_path=file_path)

                if change_status == FileChangeStatus.NEW:
                    source_doc = SourceDocument(
                        project_id=self.project_id,
                        file_path=file_path,
                        content_hash=content_hash,
                        document_type=parsed.document_type.value,
                        raw_content=raw_content,
                        parsed_metadata=parsed.frontmatter,
                    )
                    self.session.add(source_doc)
                    await self.session.flush()
                    result.indexed_files += 1

                else:  # FileChangeStatus.MODIFIED
                    source_doc = existing_map[file_path]
                    source_doc.content_hash = content_hash
                    source_doc.document_type = parsed.document_type.value
                    source_doc.raw_content = raw_content
                    source_doc.parsed_metadata = parsed.frontmatter
                    # Delete old excerpts so we re-populate fresh ones
                    await self.session.execute(
                        delete(DocumentExcerpt).where(DocumentExcerpt.document_id == source_doc.id)
                    )
                    await self.session.flush()
                    result.updated_files += 1

                # Extract entities and excerpts
                extracted = extract_from_document(
                    doc=parsed,
                    project_id=self.project_id,
                    source_doc_id=source_doc.id,
                    resolver=self.resolver,
                )

                # Persist characters
                for char in extracted.characters:
                    merged_char = await self.session.merge(char)
                    self.session.add(merged_char)
                    result.extracted_characters += 1

                # Persist locations
                for loc in extracted.locations:
                    merged_loc = await self.session.merge(loc)
                    self.session.add(merged_loc)
                    result.extracted_locations += 1

                # Persist world rules
                for rule in extracted.world_rules:
                    merged_rule = await self.session.merge(rule)
                    self.session.add(merged_rule)
                    result.extracted_rules += 1

                # Persist events
                for event in extracted.events:
                    merged_evt = await self.session.merge(event)
                    self.session.add(merged_evt)
                    result.extracted_events += 1

                # Persist excerpts
                for exc in extracted.excerpts:
                    self.session.add(exc)
                    result.extracted_excerpts += 1

            except Exception as e:
                result.errors.append(f"Error processing {file_path}: {e}")

        await self.session.commit()
        return result
