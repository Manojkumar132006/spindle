"""Spindle story ingestion, parsing, and incremental vault synchronization."""

from spindle.ingestion.extractor import (
    ExtractedEntities,
    extract_from_document,
    extract_provenance_excerpts,
)
from spindle.ingestion.hasher import (
    FileChangeStatus,
    calculate_content_hash,
    calculate_file_hash,
    detect_file_changes,
)
from spindle.ingestion.parser import (
    ParsedDocument,
    ParsedSection,
    infer_document_type,
    parse_markdown,
    parse_sections,
)
from spindle.ingestion.resolver import EntityResolver, ResolvedEntity
from spindle.ingestion.sync import SyncResult, VaultSyncEngine
from spindle.ingestion.wikilinks import (
    WikiLink,
    clean_link_target,
    extract_wikilinks,
)

__all__ = [
    "WikiLink",
    "extract_wikilinks",
    "clean_link_target",
    "calculate_content_hash",
    "calculate_file_hash",
    "detect_file_changes",
    "FileChangeStatus",
    "ParsedSection",
    "ParsedDocument",
    "infer_document_type",
    "parse_sections",
    "parse_markdown",
    "ResolvedEntity",
    "EntityResolver",
    "ExtractedEntities",
    "extract_provenance_excerpts",
    "extract_from_document",
    "SyncResult",
    "VaultSyncEngine",
]
