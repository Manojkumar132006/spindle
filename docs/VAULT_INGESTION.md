# Vault Ingestion & Synchronization Engine

The Spindle Vault Ingestion Engine bridges the author's local Obsidian Markdown files and the backend PostgreSQL narrative knowledge graph. It provides fast, incremental synchronization, deep Markdown section AST parsing, Wikilink resolution, provenance extraction, and automated ghost entity pruning.

---

## 1. Synchronization Architecture

Located in `backend/spindle/ingestion/`:
- **`hasher.py`**: Computes SHA-256 hashes of file contents to detect new, modified, unmodified, and deleted files without requiring full re-indexing.
- **`parser.py`**: Splits Markdown notes into YAML frontmatter, raw prose, heading hierarchy AST (`ParsedSection`), and extracted Wikilinks.
- **`wikilinks.py`**: Identifies Obsidian link formats: `[[Note]]`, `[[Note|Alias]]`, `[[Note#Heading]]`.
- **`resolver.py` (`EntityResolver`)**: Matches link targets to normalized database entity IDs (characters, locations, events, world rules).
- **`extractor.py`**: Extracts typed entity models (`Character`, `Location`, `Event`, `WorldRule`) and section-by-section `DocumentExcerpt` records.
- **`sync.py` (`VaultSyncEngine`)**: Transactional orchestrator coordinating the entire sync lifecycle.

---

## 2. Ingestion Rules & Document Types

The parser identifies note categories through YAML frontmatter (`type: ...`) or folder location heuristics:

| Document Type | Frontmatter / Folder Indicators | Extracted Entities |
| :--- | :--- | :--- |
| **Character** | `type: character`, `Characters/` | `Character` record (name from file title, role, status, concept, values, wound, defenses) |
| **Scene** | `type: scene`, `Manuscript/`, `pov:` | `Event` record (`Scene: <Title>`, narrative position from order/chapter, participants from POV/links) |
| **Event** | `type: event`, `Plot/Timeline/`, `when:` | `Event` record (timeline-position, participants, location, causal dependencies) |
| **Location** | `type: location`, `Worldbuilding/Locations/` | `Location` record (name, region, atmosphere, power structure) |
| **World Rule** | `type: magic`, `type: faction`, `Worldbuilding/` | `WorldRule` record (rule type, enforcement level, description) |
| **Outline** | `type: outline`, `Plot/Outline/` | `SourceDocument` with structured section excerpts for story arc context |
| **General / Research** | `type: research`, root notes | General documents indexed for semantic provenance retrieval |

---

## 3. Template Exclusion Rule

Template files located in `Templates/` (e.g. `Templates/Character.md`, `Templates/Scene.md`) contain template placeholders like `<% tp.file.title %>`. 

**Critical Rule:** `extract_from_document` explicitly detects paths starting with `templates/` or containing `/templates/` and skips entity creation. Templates are never indexed as active characters, scenes, or events.

---

## 4. Change Detection & Pruning Lifecycle

When `VaultSyncEngine.sync_vault(files)` executes:

1. **Change Classification (`hasher.py`)**:
   - `NEW`: File path does not exist in `SourceDocument`. Parsed and indexed.
   - `MODIFIED`: File path exists, but SHA-256 content hash differs. Re-parsed, old `DocumentExcerpt` records deleted, entity attributes updated.
   - `UNMODIFIED`: File path and hash match database. Skipped immediately.
   - `DELETED`: File was present in database but absent from the incoming vault sync payload.
2. **Cascading Entity Deletion on File Removal**:
   - When a note is deleted from the vault, `VaultSyncEngine` removes its `SourceDocument` along with any extracted entities (`Character`, `Event`, `Location`, `WorldRule`) whose `source_document_id` belonged to that document.
3. **Ghost Entity Pruning**:
   - At the conclusion of sync, any entity whose `source_document_id` is `NULL` or points to a non-existent document is pruned. This guarantees that stale mock data or deleted notes never pollute the author's story state.

---

## 5. Provenance Tracking (`DocumentExcerpt`)

Every heading section of every Markdown note is indexed as a `DocumentExcerpt`:
- `document_id`: Foreign key to `SourceDocument`.
- `heading`: Heading title (e.g. `## Core Motivation`, `## Narrative Beats`).
- `start_line` / `end_line`: Precise file line range.
- `excerpt_text`: Exact prose snippet.
- `embedding`: Vector embedding (pgvector) enabling semantic and hybrid retrieval.

When an AI suggestion cites supporting evidence, it points directly to these excerpts, allowing the author to verify claims against their original text.
