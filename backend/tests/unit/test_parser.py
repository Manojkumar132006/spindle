"""Unit tests for Markdown parsing, YAML frontmatter, wikilinks, and content hashing."""

from spindle.ingestion.hasher import (
    FileChangeStatus,
    calculate_content_hash,
    detect_file_changes,
)
from spindle.ingestion.parser import (
    infer_document_type,
    parse_markdown,
)
from spindle.ingestion.wikilinks import (
    clean_link_target,
    extract_wikilinks,
)
from spindle.models.base import DocumentType


def test_wikilink_extraction():
    """Test extracting simple, aliased, anchored, and embedded Obsidian wikilinks."""
    text = (
        "Elena consulted [[Aldric Voss]] and read [[The Binding Oath#Loophole|the loophole]]. "
        "She also checked ![[Varenhold Map.png]] before departing [[Varenhold]]."
    )
    links = extract_wikilinks(text)

    assert len(links) == 4

    # Link 1: [[Aldric Voss]]
    assert links[0].target == "Aldric Voss"
    assert links[0].alias is None
    assert links[0].anchor is None
    assert links[0].is_embed is False
    assert links[0].display_name == "Aldric Voss"

    # Link 2: [[The Binding Oath#Loophole|the loophole]]
    assert links[1].target == "The Binding Oath"
    assert links[1].anchor == "Loophole"
    assert links[1].alias == "the loophole"
    assert links[1].display_name == "the loophole"

    # Link 3: ![[Varenhold Map.png]]
    assert links[2].target == "Varenhold Map.png"
    assert links[2].is_embed is True

    # Link 4: [[Varenhold]]
    assert links[3].target == "Varenhold"

    assert clean_link_target("[[Aldric Voss]]") == "Aldric Voss"
    assert clean_link_target("[[The Binding Oath|Oath]]") == "The Binding Oath"
    assert clean_link_target("Plain Note Name") == "Plain Note Name"


def test_content_hashing_and_change_detection():
    """Test SHA-256 calculation and incremental change detection."""
    content1 = "Original story text."
    content2 = "Modified story text."

    hash1 = calculate_content_hash(content1)
    hash2 = calculate_content_hash(content2)

    assert hash1 != hash2
    assert len(hash1) == 64

    indexed = {
        "Chapter1.md": hash1,
        "Chapter2.md": "unchanged_hash",
        "Deleted.md": "old_hash",
    }
    incoming = {
        "Chapter1.md": content2,  # modified
        "Chapter2.md": "same_content",
        "NewChapter.md": "brand new text",  # new
    }
    # Pretend incoming Chapter2 has unchanged_hash
    unchanged_content = "same_content"
    indexed["Chapter2.md"] = calculate_content_hash(unchanged_content)

    changes = detect_file_changes(indexed, incoming)

    assert changes["Chapter1.md"][0] == FileChangeStatus.MODIFIED
    assert changes["Chapter2.md"][0] == FileChangeStatus.UNMODIFIED
    assert changes["NewChapter.md"][0] == FileChangeStatus.NEW
    assert changes["Deleted.md"][0] == FileChangeStatus.DELETED


def test_parse_character_markdown():
    """Test parsing a character note with YAML frontmatter and hierarchical sections."""
    raw = """---
type: character
role: protagonist
age: 24
first-appearance: 1
status: alive
aliases:
  - Elena
  - the scribe
---
*Example note overview.*
## Concept
A court scribe who copies the chancellor's laws.
## Psychology
### Values
Her younger brother's safety, and the truth about the oath.
### Wound
At twelve she watched her father swear the oath for their family.
## Trajectory
### Arc
She wants her own family free of the oath.
"""
    doc = parse_markdown(raw, file_path="Characters/Elena Vareth.md")

    assert doc.document_type == DocumentType.CHARACTER
    assert doc.frontmatter["role"] == "protagonist"
    assert doc.frontmatter["age"] == 24
    assert "Elena" in doc.frontmatter["aliases"]

    # Check sections
    section_headings = [s.heading for s in doc.sections]
    assert "Concept" in section_headings
    assert "Psychology" in section_headings
    assert "Values" in section_headings
    assert "Wound" in section_headings
    assert "Trajectory" in section_headings
    assert "Arc" in section_headings

    values_sec = next(s for s in doc.sections if s.heading == "Values")
    assert values_sec.parent_heading == "Psychology"
    assert "younger brother" in values_sec.content
    assert values_sec.start_line > doc.frontmatter_end_line


def test_parse_scene_with_wikilinks():
    """Test parsing a scene note with frontmatter wikilinks and body prose."""
    raw = """---
type: scene
chapter: 7
act: 2
order: 10
pov: "[[Elena Vareth|Elena]]"
place: "[[Varenhold]]"
summary: Elena copies the Binding Oath and finds the loophole.
---
Elena copied the oath while the archivist watched.
[[The Binding Oath]] bound every family in [[Varenhold]].
Nothing said what happened if the Regency fell.
"""
    doc = parse_markdown(raw, file_path="Manuscript/Chapter 7.md")

    assert doc.document_type == DocumentType.SCENE
    assert doc.frontmatter["chapter"] == 7
    assert doc.frontmatter["order"] == 10

    # Links from frontmatter and body
    link_targets = {link.target for link in doc.wikilinks}
    assert "Elena Vareth" in link_targets
    assert "Varenhold" in link_targets
    assert "The Binding Oath" in link_targets


def test_infer_document_type_heuristics():
    """Test document type inference when frontmatter is missing or partial."""
    assert infer_document_type({"type": "magic"}, "any/path.md") == DocumentType.WORLDBUILDING
    assert infer_document_type({}, "Characters/Aldric.md") == DocumentType.CHARACTER
    assert infer_document_type({}, "Manuscript/Act 1/Scene 1.md") == DocumentType.SCENE
    assert infer_document_type({}, "Worldbuilding/History/The Oath.md") == DocumentType.EVENT
    assert infer_document_type({}, "Worldbuilding/Locations/Capital.md") == DocumentType.LOCATION
    assert infer_document_type({}, "Random/Notes.md") == DocumentType.GENERAL
