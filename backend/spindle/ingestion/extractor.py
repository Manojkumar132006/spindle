"""Extract structured narrative models and provenance excerpts from parsed documents."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from spindle.ingestion.parser import ParsedDocument
from spindle.ingestion.resolver import EntityResolver
from spindle.ingestion.wikilinks import clean_link_target
from spindle.models.base import (
    CanonStatus,
    DocumentType,
    EnforcementLevel,
    RuleType,
)
from spindle.models.document import DocumentExcerpt
from spindle.models.entity import Character, Location, WorldRule
from spindle.models.event import Event


@dataclass
class ExtractedEntities:
    """Container holding entities and provenance excerpts extracted from a document."""

    characters: list[Character] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    world_rules: list[WorldRule] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    excerpts: list[DocumentExcerpt] = field(default_factory=list)


def _get_note_title(file_path: str) -> str:
    """Derive entity note title from file path stem."""
    return Path(file_path).stem


def _find_section_content(doc: ParsedDocument, *heading_names: str) -> str | None:
    """Find content of the first section whose heading matches any of the given names."""
    normalized_targets = {h.lower() for h in heading_names}
    for sec in doc.sections:
        if sec.heading.lower() in normalized_targets:
            return sec.content
    return None


def extract_provenance_excerpts(
    doc: ParsedDocument,
    source_doc_id: uuid.UUID,
) -> list[DocumentExcerpt]:
    """Create DocumentExcerpt records for all non-empty sections of a parsed document."""
    excerpts: list[DocumentExcerpt] = []
    for sec in doc.sections:
        if sec.content.strip():
            excerpt = DocumentExcerpt(
                document_id=source_doc_id,
                excerpt_text=sec.content,
                start_line=sec.start_line,
                end_line=sec.end_line,
                heading=sec.heading,
                metadata_json={
                    "level": sec.level,
                    "parent_heading": sec.parent_heading,
                    "wikilinks": [link.target for link in sec.wikilinks],
                },
            )
            excerpts.append(excerpt)
    return excerpts


def extract_from_document(
    doc: ParsedDocument,
    project_id: uuid.UUID,
    source_doc_id: uuid.UUID,
    resolver: EntityResolver,
) -> ExtractedEntities:
    """Extract relational entities and excerpts based on document type and schema."""
    extracted = ExtractedEntities()
    note_title = _get_note_title(doc.file_path)
    fm = doc.frontmatter

    # Always extract section excerpts for source provenance
    extracted.excerpts = extract_provenance_excerpts(doc, source_doc_id)

    # 1. Character Extraction
    if doc.document_type == DocumentType.CHARACTER:
        aliases: list[str] = []
        raw_aliases = fm.get("aliases")
        if isinstance(raw_aliases, list):
            aliases = [str(a).strip() for a in raw_aliases if a]
        elif isinstance(raw_aliases, str) and raw_aliases.strip():
            aliases = [raw_aliases.strip()]

        char_id, _ = resolver.get_or_create_id(
            name=note_title,
            entity_type="character",
            aliases=aliases,
        )

        concept = _find_section_content(doc, "Concept")
        values = _find_section_content(doc, "Values")
        wound = _find_section_content(doc, "Wound")
        defenses = _find_section_content(doc, "Defenses")
        personality = _find_section_content(doc, "Personality", "Psychology")
        arc = _find_section_content(doc, "Arc", "Trajectory")

        status_str = str(fm.get("status", "alive")).lower()
        role_str = fm.get("role")
        if role_str:
            role_str = str(role_str).lower()

        char = Character(
            id=char_id,
            project_id=project_id,
            name=note_title,
            aliases=aliases,
            role=role_str,
            description=concept,
            personality=personality,
            motivations=values,
            fears=wound or defenses,
            secrets=None,
            current_state=status_str,
            canon_status=CanonStatus.CONFIRMED,
            source_document_id=source_doc_id,
            metadata_json={
                "age": fm.get("age"),
                "first_appearance": fm.get("first-appearance"),
                "arc": arc,
            },
        )
        extracted.characters.append(char)

    # 2. Location Extraction
    elif doc.document_type == DocumentType.LOCATION:
        loc_id, _ = resolver.get_or_create_id(
            name=note_title,
            entity_type="location",
        )
        first_impressions = _find_section_content(doc, "What a visitor notices first")
        power_structure = _find_section_content(doc, "Who holds power here")
        narrative_needs = _find_section_content(doc, "What the story needs from it")

        location = Location(
            id=loc_id,
            project_id=project_id,
            name=note_title,
            kind=fm.get("kind"),
            region=fm.get("region"),
            description=first_impressions or doc.body.strip()[:500],
            attributes={
                "power_structure": power_structure,
                "narrative_purpose": narrative_needs,
            },
            source_document_id=source_doc_id,
        )
        extracted.locations.append(location)

    # 3. Event Extraction
    elif doc.document_type == DocumentType.EVENT:
        event_id, _ = resolver.get_or_create_id(
            name=note_title,
            entity_type="event",
        )
        when_str = str(fm.get("when", "")) if fm.get("when") is not None else None

        # Determine chronological and narrative orders
        raw_order = fm.get("order")
        order_num: float = 0.0
        if raw_order is not None:
            try:
                order_num = float(raw_order)
            except (ValueError, TypeError):
                order_num = 0.0

        # Participants from frontmatter
        people_raw = fm.get("people", [])
        participants: list[str] = []
        if isinstance(people_raw, list):
            participants = [clean_link_target(str(p)) for p in people_raw]
        elif isinstance(people_raw, str):
            participants = [clean_link_target(people_raw)]

        # Place from frontmatter
        place_ref = fm.get("place")
        loc_id: uuid.UUID | None = None
        if place_ref:
            loc_name = clean_link_target(str(place_ref))
            resolved_loc = resolver.resolve(loc_name)
            if resolved_loc:
                loc_id = resolved_loc.id

        what_changed = _find_section_content(doc, "What changed because of it")
        description = what_changed or doc.body.strip()

        event = Event(
            id=event_id,
            project_id=project_id,
            title=note_title,
            description=description,
            narrative_position=order_num,
            chronological_timestamp=when_str,
            chronological_order=order_num if order_num > 0 else None,
            participants=participants,
            location_id=loc_id,
            causal_dependencies=[],
            confidence=1.0,
            canon_status=CanonStatus.CONFIRMED,
            source_document_id=source_doc_id,
            metadata_json={"raw_place": place_ref},
        )
        extracted.events.append(event)

    # 4. WorldRule Extraction
    elif doc.document_type == DocumentType.WORLDBUILDING:
        rule_id, _ = resolver.get_or_create_id(
            name=note_title,
            entity_type="world_rule",
        )
        accessibility = _find_section_content(doc, "Accessibility")
        cost = _find_section_content(doc, "Cost")
        effect = _find_section_content(doc, "Effect")
        acceptance = _find_section_content(doc, "Acceptance")
        narrative_needs = _find_section_content(doc, "What the story needs from it")

        desc_parts = []
        if effect:
            desc_parts.append(f"Effect: {effect}")
        if cost:
            desc_parts.append(f"Cost: {cost}")
        if accessibility:
            desc_parts.append(f"Accessibility: {accessibility}")
        if not desc_parts:
            desc_parts.append(doc.body.strip()[:1000])

        rule_type = RuleType.MAGIC if fm.get("type") == "magic" else RuleType.GENERAL
        rule = WorldRule(
            id=rule_id,
            project_id=project_id,
            name=note_title,
            description="\n\n".join(desc_parts),
            rule_type=rule_type.value,
            enforcement_level=EnforcementLevel.HARD.value,
            source_document_id=source_doc_id,
            metadata_json={
                "acceptance": acceptance,
                "narrative_purpose": narrative_needs,
            },
        )
        extracted.world_rules.append(rule)

    # 5. Scene Extraction (Creates Scene Event if order is specified)
    elif doc.document_type == DocumentType.SCENE:
        raw_order = fm.get("order")
        if raw_order is not None or "chapter" in fm:
            order_num = 0.0
            if raw_order is not None:
                try:
                    order_num = float(raw_order)
                except (ValueError, TypeError):
                    order_num = 0.0
            elif "chapter" in fm:
                try:
                    order_num = float(fm["chapter"])
                except (ValueError, TypeError):
                    order_num = 0.0

            scene_id, _ = resolver.get_or_create_id(
                name=note_title,
                entity_type="event",
            )

            # Participants (POV and mentions)
            participants = []
            pov_ref = fm.get("pov")
            if pov_ref:
                participants.append(clean_link_target(str(pov_ref)))

            summary = fm.get("summary") or doc.body.strip()[:300]
            scene_event = Event(
                id=scene_id,
                project_id=project_id,
                title=f"Scene: {note_title}",
                description=summary,
                narrative_position=order_num,
                chronological_timestamp=None,
                chronological_order=None,
                participants=participants,
                confidence=1.0,
                canon_status=CanonStatus.CONFIRMED,
                source_document_id=source_doc_id,
                metadata_json={
                    "chapter": fm.get("chapter"),
                    "act": fm.get("act"),
                    "goal": fm.get("goal"),
                    "conflict": fm.get("conflict"),
                    "outcome": fm.get("outcome"),
                    "place": fm.get("place"),
                },
            )
            extracted.events.append(scene_event)

    return extracted
