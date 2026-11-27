# Database Schema & Data Models

Spindle persists the author's narrative universe in **PostgreSQL 16** with the **`pgvector`** extension for semantic excerpt search. All models use **SQLAlchemy 2.0 async ORM** with UUID primary keys and strict foreign key relationships.

---

## 1. Entity-Relationship Overview

```
                      ┌───────────────┐
                      │    Project    │
                      └───────┬───────┘
                              │ 1:N
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐    ┌───────▼────────┐    ┌───────▼────────┐
│ SourceDocument │    │   Character    │    │     Event      │
└───────┬────────┘    └───────┬────────┘    └────────────────┘
        │ 1:N                 │ 1:N
┌───────▼────────┐    ┌───────▼────────┐
│DocumentExcerpt │    │Char. Knowledge │
│   (pgvector)   │    └────────────────┘
└────────────────┘
```

---

## 2. Models Detail

### 1. `Project` (`spindle/models/project.py`)
Multi-universe partition.
- `id`: UUID primary key.
- `name`: Story or universe title.
- `description`: Optional premise description.
- `created_at` / `updated_at`: UTC timestamps.

### 2. `SourceDocument` (`spindle/models/document.py`)
Tracks every ingested Markdown file from the author's Obsidian vault.
- `id`: UUID.
- `project_id`: FK $\to$ `projects.id` (CASCADE).
- `file_path`: Relative vault path (e.g. `Characters/Billy.md`).
- `content_hash`: SHA-256 string for change detection.
- `document_type`: Enum (`character`, `scene`, `event`, `location`, `worldbuilding`, `outline`, `research`, `general`).
- `raw_content`: Full markdown text.
- `parsed_metadata`: Parsed YAML frontmatter dict.

### 3. `DocumentExcerpt` (`spindle/models/document.py`)
Heading-level sections of markdown documents used for provenance and retrieval.
- `id`: UUID.
- `document_id`: FK $\to$ `source_documents.id` (CASCADE).
- `heading`: Section heading text (e.g. `## Core Motivation`).
- `start_line` / `end_line`: File line bounds.
- `excerpt_text`: Exact prose snippet.
- `embedding`: Vector (1536 dimensions) using pgvector.

### 4. `Character` (`spindle/models/entity.py`)
Psychological and physical narrative state of a character.
- `id`: UUID.
- `project_id`: FK $\to$ `projects.id` (CASCADE).
- `name`: Character name (e.g. `Billy`).
- `aliases`: JSON list of strings (e.g. `["the courier"]`).
- `role`: Role string (`protagonist`, `antagonist`, `supporting`, `minor`).
- `current_state`: Vitality state (`alive`, `deceased`, `missing`).
- `personality`, `motivations`, `fears`, `secrets`: Psychological traits extracted from profile notes.
- `source_document_id`: FK $\to$ `source_documents.id` (SET NULL).

### 5. `Event` (`spindle/models/event.py`)
Chronological or narrative timeline occurrence.
- `id`: UUID.
- `project_id`: FK $\to$ `projects.id` (CASCADE).
- `title`: Event or scene title.
- `description`: Summary of what occurred.
- `narrative_position`: Float order in book reading sequence (e.g. `1.0`, `1.5`, `2.0`).
- `chronological_order`: In-world chronological order (can differ from manuscript sequence).
- `participants`: JSON list of character names involved.
- `causal_dependencies`: JSON list of prerequisite event titles.
- `canon_status`: Status string (`extracted`, `confirmed`, `hypothetical`).
- `source_document_id`: FK $\to$ `source_documents.id` (SET NULL).

### 6. `CharacterKnowledge` (`spindle/models/knowledge.py`)
Epistemic ledger tracking who knows what and when.
- `id`: UUID.
- `character_id`: FK $\to$ `characters.id` (CASCADE).
- `fact_or_event_id`: Identifier of the learned secret, plot event, or lore fact.
- `knowledge_status`: `confirmed`, `suspected`, `false_belief`.
- `acquired_at`: Narrative position when the knowledge was acquired.

### 7. `WorldRule` (`spindle/models/entity.py`)
Inviolable universe laws (magic systems, physics limits, legal codes).
- `id`: UUID.
- `project_id`: FK $\to$ `projects.id` (CASCADE).
- `name`: Rule title (e.g. `No Instant Teleportation`).
- `description`: Detailed operational parameters.
- `rule_type`: `magic`, `physics`, `biological`, `legal`, `social`.
- `enforcement_level`: `hard` (blocks generation) or `soft` (emits warning).

### 8. `Suggestion` (`spindle/models/suggestion.py`)
AI-generated creative proposals.
- `id`: UUID.
- `project_id`: FK $\to$ `projects.id` (CASCADE).
- `suggestion_type`: `plot_point`, `side_story`, `continuity_analysis`.
- `title`: Suggestion title.
- `premise`: 1-2 sentence concept.
- `detailed_content`: JSON object holding scene beats, character lists, and consequences.
- `supporting_evidence`: JSON list of cited vault files.
- `assumptions`: JSON list of narrative assumptions made.
- `validation_results`: Full `ValidationReport` dict from `ConstraintEngine`.
- `approval_status`: Lifecycle state (`pending_author_approval`, `approved`, `edited`, `rejected`, `committed`).
- `rejection_reason`: Mandatory rationale if rejected.
- `branch_id`: Optional FK to hypothetical `NarrativeBranch`.
