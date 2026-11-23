"""Non-destructive canon commitment service integrating approved suggestions into story canon."""

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.core.lifecycle import validate_lifecycle_transition
from spindle.ingestion.hasher import calculate_content_hash
from spindle.ingestion.parser import parse_markdown
from spindle.models.base import ApprovalStatus, CanonStatus, DocumentType
from spindle.models.document import DocumentExcerpt, SourceDocument
from spindle.models.event import Event
from spindle.models.suggestion import Suggestion


@dataclass
class CommitResult:
    """Outcome of committing an approved suggestion to canon."""

    suggestion_id: uuid.UUID
    project_id: uuid.UUID
    file_path: str
    content_hash: str
    document_id: uuid.UUID
    event_id: uuid.UUID
    markdown_content: str
    committed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def sanitize_filename(title: str) -> str:
    """Sanitize suggestion title for use as an Obsidian note filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or "Untitled Suggestion"


class CanonCommitService:
    """Service guaranteeing non-destructive commitment of approved suggestions into author canon."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def generate_markdown(self, suggestion: Suggestion) -> str:
        """Format an approved suggestion into native Obsidian Markdown with frontmatter."""
        characters = suggestion.detailed_content.get("involved_characters", [])
        char_yaml = "\n".join(f'  - "[[{c}]]"' for c in characters) if characters else "  []"

        raw_beats = (
            suggestion.detailed_content.get("scene_beats")
            or suggestion.detailed_content.get("beats")
            or suggestion.detailed_content.get("beat")
            or []
        )
        if isinstance(raw_beats, str):
            beats = [raw_beats]
        elif isinstance(raw_beats, list):
            beats = raw_beats
        else:
            beats = []

        beats_text = ""
        if beats:
            beats_text = "## Outline & Scene Beats\n" + "\n".join(f"- {b}" for b in beats) + "\n\n"

        evidence_text = ""
        if suggestion.supporting_evidence:
            evidence_text = (
                "## Supporting Evidence & Canon Sources\n"
                + "\n".join(
                    f"- [[{clean_src}]]" if not clean_src.startswith("[[") else f"- {clean_src}"
                    for clean_src in suggestion.supporting_evidence
                )
                + "\n\n"
            )

        frontmatter = f"""---
type: scene
title: "{suggestion.title}"
summary: "{suggestion.premise}"
status: canon
source_suggestion_id: "{suggestion.id}"
suggestion_type: "{suggestion.suggestion_type}"
committed_at: "{datetime.now(UTC).isoformat()}"
characters:
{char_yaml}
---
"""
        body = f"""# {suggestion.title}

## Premise
{suggestion.premise}

{beats_text}{evidence_text}## Assumptions
{chr(10).join(f"- {a}" for a in suggestion.assumptions) if suggestion.assumptions else "- None stated."}
"""
        return frontmatter + "\n" + body

    async def _resolve_unique_filepath(
        self,
        project_id: uuid.UUID,
        destination_folder: str,
        title: str,
    ) -> str:
        """Determine a safe, non-destructive file path ensuring existing manuscripts are never overwritten."""
        clean_name = sanitize_filename(title)
        base_folder = destination_folder.strip("/\\")
        candidate_path = f"{base_folder}/{clean_name}.md"

        # Check existing source documents for project
        stmt = select(SourceDocument.file_path).where(SourceDocument.project_id == project_id)
        existing_paths = set((await self.session.execute(stmt)).scalars().all())

        counter = 1
        while candidate_path in existing_paths:
            counter += 1
            candidate_path = f"{base_folder}/{clean_name} ({counter}).md"

        return candidate_path

    async def commit_suggestion(
        self,
        suggestion: Suggestion,
        destination_folder: str = "Manuscript/Side Stories",
    ) -> CommitResult:
        """Commit an approved or edited suggestion into project canon.

        Guarantees:
        1. Lifecycle transition validation (cannot commit unapproved or rejected suggestions).
        2. Non-destructive file path resolution (never overwrites existing manuscript files).
        3. Canonical database record creation with CONFIRMED status.
        4. Complete audit log linking committed document to original suggestion and author edits.
        """
        # 1. Enforce lifecycle transition
        validate_lifecycle_transition(suggestion.approval_status, ApprovalStatus.COMMITTED)

        # 2. Determine unique, non-destructive file path
        unique_file_path = await self._resolve_unique_filepath(
            project_id=suggestion.project_id,
            destination_folder=destination_folder,
            title=suggestion.title,
        )

        # 3. Generate native Obsidian markdown prose
        markdown_content = self.generate_markdown(suggestion)
        content_hash = calculate_content_hash(markdown_content)

        # 4. Parse sections and create SourceDocument
        parsed_doc = parse_markdown(markdown_content, file_path=unique_file_path)
        source_doc = SourceDocument(
            project_id=suggestion.project_id,
            file_path=unique_file_path,
            content_hash=content_hash,
            document_type=DocumentType.SCENE.value,
            raw_content=markdown_content,
            parsed_metadata=parsed_doc.frontmatter,
        )
        self.session.add(source_doc)
        await self.session.flush()

        # Create DocumentExcerpts for provenance
        for sec in parsed_doc.sections:
            if sec.content.strip():
                excerpt = DocumentExcerpt(
                    document_id=source_doc.id,
                    excerpt_text=sec.content,
                    start_line=sec.start_line,
                    end_line=sec.end_line,
                    heading=sec.heading,
                    metadata_json={
                        "source": "committed_suggestion",
                        "suggestion_id": str(suggestion.id),
                    },
                )
                self.session.add(excerpt)

        # 5. Create canonical Event in narrative state
        narrative_pos = 0.0
        if "act" in suggestion.detailed_content:
            try:
                narrative_pos = float(suggestion.detailed_content["act"])
            except (ValueError, TypeError):
                pass

        event = Event(
            project_id=suggestion.project_id,
            title=suggestion.title,
            description=suggestion.premise,
            narrative_position=narrative_pos,
            chronological_timestamp=None,
            chronological_order=narrative_pos,
            participants=suggestion.detailed_content.get("involved_characters", []),
            causal_dependencies=suggestion.detailed_content.get("causal_dependencies", []),
            confidence=1.0,
            canon_status=CanonStatus.CONFIRMED.value,
            source_document_id=source_doc.id,
            metadata_json={"committed_from_suggestion": str(suggestion.id)},
        )
        self.session.add(event)
        await self.session.flush()

        # 6. Update suggestion status and record audit log
        suggestion.approval_status = ApprovalStatus.COMMITTED.value
        audit_entry = {
            "action": "committed_to_canon",
            "committed_at": datetime.now(UTC).isoformat(),
            "destination_file_path": unique_file_path,
            "source_document_id": str(source_doc.id),
            "event_id": str(event.id),
            "original_title": suggestion.title,
            "has_author_edits": bool(suggestion.author_edits),
        }
        # Append audit entry to suggestion detailed_content
        current_history = suggestion.detailed_content.get("audit_history", [])
        current_history.append(audit_entry)
        suggestion.detailed_content["audit_history"] = current_history

        await self.session.commit()

        return CommitResult(
            suggestion_id=suggestion.id,
            project_id=suggestion.project_id,
            file_path=unique_file_path,
            content_hash=content_hash,
            document_id=source_doc.id,
            event_id=event.id,
            markdown_content=markdown_content,
        )
