# Spindle REST API Reference

The Spindle backend is an asynchronous Python 3.12+ FastAPI service providing endpoints for vault synchronization, narrative state querying, multi-agent story generation, constraint validation, and canon suggestion lifecycle management.

Base URL: `http://localhost:8000` (default in local development)
Prefix: `/api/v1`

---

## 1. Authentication & Common Headers

All project-specific routes require the `X-Project-ID` HTTP header identifying the active story project UUID. If omitted or not found, an active project is auto-selected or created as a fallback.

```http
X-Project-ID: 34b5ab17-f658-4448-a19a-c5b16aaf0fb3
Content-Type: application/json
```

---

## 2. System & Health Endpoints

### `GET /health`
Verifies backend service availability and reports status.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "environment": "development"
}
```

---

## 3. Project Management

### `GET /api/v1/projects`
List all registered story projects.

**Response `200 OK`**:
```json
[
  {
    "id": "34b5ab17-f658-4448-a19a-c5b16aaf0fb3",
    "name": "Default Project",
    "description": "Primary story universe",
    "created_at": "2026-10-21T14:00:00Z"
  }
]
```

### `POST /api/v1/projects`
Create a new story universe.

**Request Body**:
```json
{
  "name": "The Vey Chronicles",
  "description": "High fantasy secondary world"
}
```

**Response `201 Created`**:
```json
{
  "id": "e2a9041a-8c76-4d1a-98de-4011fa990001",
  "name": "The Vey Chronicles",
  "description": "High fantasy secondary world",
  "created_at": "2026-11-27T12:00:00Z"
}
```

---

## 4. Vault Synchronization & Ingestion

### `POST /api/v1/vault/sync`
Synchronize an array of vault markdown files with the narrative knowledge graph. Uses deterministic SHA-256 change detection. Automatically parses frontmatter, extracts character profiles, locations, events, and world rules, while pruning orphaned ghost entities.

**Request Body**:
```json
{
  "files": [
    {
      "path": "Characters/Billy.md",
      "content": "---\ntype: character\nrole: antagonist\nage: 19\n---\n# Billy\n\n## Concept\nA rogue operative navigating the train lines.",
      "content_hash": "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"
    },
    {
      "path": "Manuscript/Train.md",
      "content": "---\ntype: scene\npov: \"[[Billy]]\"\nchapter: 1\norder: 1\n---\nRain fell as though the clouds were in mourning...",
      "content_hash": "c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffc6a7288746a034f"
    }
  ]
}
```

**Response `200 OK`**:
```json
{
  "status": "success",
  "total_files_received": 2,
  "indexed_count": 2,
  "updated_count": 0,
  "skipped_count": 0,
  "deleted_count": 0,
  "extracted_characters": 1,
  "extracted_events": 1,
  "extracted_locations": 0,
  "extracted_rules": 0,
  "errors": []
}
```

### `GET /api/v1/vault/status`
Retrieve current ingestion metrics and index freshness.

**Response `200 OK`**:
```json
{
  "project_id": "34b5ab17-f658-4448-a19a-c5b16aaf0fb3",
  "total_documents": 8,
  "last_synced_at": "2026-11-27T14:30:00Z",
  "status": "idle"
}
```

---

## 5. Narrative State & Metrics

### `GET /api/v1/story/overview`
Fetches a high-level narrative health card including character counts, chronological events, world rules, open threads, and active constraints.

**Response `200 OK`**:
```json
{
  "project_id": "34b5ab17-f658-4448-a19a-c5b16aaf0fb3",
  "project_name": "Default Project",
  "characters_count": 1,
  "events_count": 1,
  "locations_count": 0,
  "world_rules_count": 0,
  "constraints_count": 0,
  "open_threads_count": 0,
  "documents_count": 8
}
```

### `GET /api/v1/story/characters`
List all characters established in canon.

**Response `200 OK`**:
```json
[
  {
    "id": "d5e8b31c-9e63-49d3-93f1-42b1d8e0b9b3",
    "name": "Billy",
    "role": "antagonist",
    "current_state": "alive",
    "description": "A rogue operative navigating the train lines.",
    "aliases": []
  }
]
```

---

## 6. Generation & Multi-Agent Operations

### `POST /api/v1/generate/plot-point`
Generate a canon-consistent, constraint-checked scene continuation.

**Request Body**:
```json
{
  "request": "Billy encounters resistance in the passenger car while trying to locate the manifest.",
  "narrative_position": 1.0,
  "characters": ["Billy"]
}
```

**Response `200 OK`**:
```json
{
  "id": "b1e7790b-0441-4770-9831-294fae72e118",
  "project_id": "34b5ab17-f658-4448-a19a-c5b16aaf0fb3",
  "suggestion_type": "plot_point",
  "title": "Confrontation on the Express",
  "premise": "Billy navigates through the passenger car under the cover of the storm.",
  "detailed_content": {
    "act": 1,
    "involved_characters": ["Billy"],
    "scene_beats": [
      "Billy quietly checks the locks on the storage compartment.",
      "A conductor passes through, forcing Billy to take a seat beside a sleeping passenger.",
      "He locates the briefcase matching the manifest description."
    ]
  },
  "supporting_evidence": ["Manuscript/Train.md", "Characters/Billy.md"],
  "assumptions": ["The conductor does not inspect passenger tickets during the storm."],
  "validation_results": {
    "overall_outcome": "PASS",
    "is_valid": true,
    "has_hard_failures": false,
    "summary": "Validation PASSED: Proposal satisfies all active narrative constraints."
  },
  "approval_status": "pending_author_approval"
}
```

### `POST /api/v1/generate/side-story`
Generate a canon-compatible standalone side story vignette.

### `POST /api/v1/generate/continuity-analysis`
Analyze continuity, epistemic state, and rule compliance across a proposed narrative turn.

### `POST /api/v1/generate/explore-branches`
Synthesizes multiple divergent narrative pathways at the specified narrative position **without requiring a custom prompt**.

**Request Body**:
```json
{
  "narrative_position": 1.0,
  "branch_count": 3,
  "target_characters": ["Billy"]
}
```

**Response `200 OK`**:
Returns an array of `SuggestionResponse` objects, each representing a unique dramatic angle (e.g. *Tactical Escalation*, *Covert Investigation*, *Forced Alliance*, *Retreat*), complete with scene beats, causal consequences, and validation results.

---

## 7. Suggestion Lifecycle & Commitment Gate

### `GET /api/v1/suggestions`
List all suggestions for the project. Optional query params: `status`, `type`.

### `GET /api/v1/suggestions/{id}`
Retrieve a single suggestion and its detailed validation diagnostic report.

### `POST /api/v1/suggestions/{id}/approve`
Author approves the suggestion.
```json
{ "notes": "Approved for inclusion in Chapter 2." }
```

### `POST /api/v1/suggestions/{id}/reject`
Author rejects the suggestion with mandatory rationale.
```json
{ "reason": "Billy would not openly confront the conductor at this stage." }
```

### `PUT /api/v1/suggestions/{id}/edit`
Modify suggestion title, premise, or scene beats while preserving revision history.

### `POST /api/v1/suggestions/{id}/commit`
Non-destructively commits an approved suggestion into the author's vault canon. Generates a new Markdown file with frontmatter in `Manuscript/Side Stories/` (or custom folder) with full provenance metadata.

**Request Body**:
```json
{ "destination_folder": "Manuscript/Side Stories" }
```

**Response `200 OK`**:
```json
{
  "status": "committed",
  "suggestion_id": "b1e7790b-0441-4770-9831-294fae72e118",
  "file_path": "Manuscript/Side Stories/Confrontation on the Express.md",
  "document_id": "0e1f7ce8-bcdd-4f75-bb76-09adf8ee2b94",
  "event_id": "55f0df05-a933-4296-9535-e0589be231e2",
  "committed_at": "2026-11-27T15:00:00Z"
}
```
