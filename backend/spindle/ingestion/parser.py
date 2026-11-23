"""Markdown, YAML frontmatter, and section AST parser for Obsidian vaults."""

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from spindle.ingestion.hasher import calculate_content_hash
from spindle.ingestion.wikilinks import WikiLink, extract_wikilinks
from spindle.models.base import DocumentType

FRONTMATTER_REGEX = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.+)$")


@dataclass
class ParsedSection:
    """A section of Markdown content under a specific heading."""

    heading: str
    level: int
    content: str
    start_line: int
    end_line: int
    parent_heading: str | None = None
    wikilinks: list[WikiLink] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Structured representation of a parsed Obsidian Markdown document."""

    file_path: str
    frontmatter: dict[str, Any]
    body: str
    document_type: DocumentType
    sections: list[ParsedSection]
    wikilinks: list[WikiLink]
    content_hash: str
    raw_content: str
    frontmatter_end_line: int = 0


def infer_document_type(frontmatter: dict[str, Any], file_path: str) -> DocumentType:
    """Infer document type from YAML frontmatter or vault file path."""
    fm_type = str(frontmatter.get("type", "")).strip().lower()

    type_mapping = {
        "character": DocumentType.CHARACTER,
        "scene": DocumentType.SCENE,
        "event": DocumentType.EVENT,
        "location": DocumentType.LOCATION,
        "magic": DocumentType.WORLDBUILDING,
        "world_rule": DocumentType.WORLDBUILDING,
        "worldrule": DocumentType.WORLDBUILDING,
        "faction": DocumentType.WORLDBUILDING,
        "people": DocumentType.WORLDBUILDING,
        "outline": DocumentType.OUTLINE,
        "research": DocumentType.RESEARCH,
    }

    if fm_type in type_mapping:
        return type_mapping[fm_type]

    # Path heuristics
    normalized_path = f"/{file_path.replace('\\', '/').lower().lstrip('/')}"
    if "/characters/" in normalized_path:
        return DocumentType.CHARACTER
    if "/manuscript/" in normalized_path:
        return DocumentType.SCENE
    if (
        "/plot/timeline" in normalized_path
        or "/worldbuilding/history" in normalized_path
        or "timeline" in normalized_path
        or "/history/" in normalized_path
    ):
        return DocumentType.EVENT
    if "/worldbuilding/locations" in normalized_path or "/locations/" in normalized_path:
        return DocumentType.LOCATION
    if "/worldbuilding/" in normalized_path:
        return DocumentType.WORLDBUILDING
    if "/plot/" in normalized_path or "outline" in normalized_path:
        return DocumentType.OUTLINE
    if "/research/" in normalized_path:
        return DocumentType.RESEARCH

    return DocumentType.GENERAL


def parse_sections(body_text: str, line_offset: int = 0) -> list[ParsedSection]:
    """Parse Markdown headings into hierarchical sections with exact line ranges."""
    lines = body_text.splitlines()
    if not lines:
        return []

    sections: list[ParsedSection] = []
    heading_stack: list[tuple[int, str]] = []  # (level, heading_name)

    current_heading: str | None = None
    current_level = 0
    current_start = line_offset + 1
    current_lines: list[str] = []

    for idx, line in enumerate(lines):
        line_num = line_offset + idx + 1
        heading_match = HEADING_REGEX.match(line)

        if heading_match:
            # If we had a previous section, save it
            if current_heading is not None:
                section_text = "\n".join(current_lines).strip()
                parent = None
                for lvl, name in reversed(heading_stack[:-1]):
                    if lvl < current_level:
                        parent = name
                        break

                sections.append(
                    ParsedSection(
                        heading=current_heading,
                        level=current_level,
                        content=section_text,
                        start_line=current_start,
                        end_line=line_num - 1,
                        parent_heading=parent,
                        wikilinks=extract_wikilinks(section_text),
                    )
                )

            current_level = len(heading_match.group(1))
            current_heading = heading_match.group(2).strip()
            current_start = line_num
            current_lines = []

            # Adjust heading stack
            while heading_stack and heading_stack[-1][0] >= current_level:
                heading_stack.pop()
            heading_stack.append((current_level, current_heading))
        else:
            current_lines.append(line)

    # Add final section
    if current_heading is not None:
        section_text = "\n".join(current_lines).strip()
        parent = None
        for lvl, name in reversed(heading_stack[:-1]):
            if lvl < current_level:
                parent = name
                break

        sections.append(
            ParsedSection(
                heading=current_heading,
                level=current_level,
                content=section_text,
                start_line=current_start,
                end_line=line_offset + len(lines),
                parent_heading=parent,
                wikilinks=extract_wikilinks(section_text),
            )
        )

    return sections


def parse_markdown(raw_content: str, file_path: str = "") -> ParsedDocument:
    """Parse an Obsidian Markdown document, extracting frontmatter, sections, and links."""
    content_hash = calculate_content_hash(raw_content)
    frontmatter: dict[str, Any] = {}
    body = raw_content
    frontmatter_end_line = 0

    fm_match = FRONTMATTER_REGEX.match(raw_content)
    if fm_match:
        fm_raw = fm_match.group(1)
        try:
            parsed_fm = yaml.safe_load(fm_raw)
            if isinstance(parsed_fm, dict):
                frontmatter = parsed_fm
        except Exception:
            frontmatter = {}

        frontmatter_lines = fm_match.group(0).count("\n")
        frontmatter_end_line = frontmatter_lines
        body = raw_content[fm_match.end() :]

    doc_type = infer_document_type(frontmatter, file_path)
    sections = parse_sections(body, line_offset=frontmatter_end_line)

    # Extract all wikilinks from body and frontmatter
    wikilinks = extract_wikilinks(body)
    # Check frontmatter values for links
    for val in frontmatter.values():
        if isinstance(val, str):
            wikilinks.extend(extract_wikilinks(val))
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    wikilinks.extend(extract_wikilinks(item))

    # Deduplicate wikilinks preserving order
    seen_links = set()
    unique_links: list[WikiLink] = []
    for link in wikilinks:
        if link.raw not in seen_links:
            seen_links.add(link.raw)
            unique_links.append(link)

    return ParsedDocument(
        file_path=file_path,
        frontmatter=frontmatter,
        body=body,
        document_type=doc_type,
        sections=sections,
        wikilinks=unique_links,
        content_hash=content_hash,
        raw_content=raw_content,
        frontmatter_end_line=frontmatter_end_line,
    )
