# Spindle: Master Task Checklist & Implementation Plan

This document outlines the breakdown of tasks across all stages of the Spindle MVP development. Each task is granular, testable, and concludes with an explicit review gate.

---

## Stage 1: Foundation & Infrastructure

### Task 1.1: Monorepo & Python Environment Setup
- [x] Initialize monorepo directory layout (`backend/`, `obsidian-plugin/`, `web/`, `docs/`).
- [x] Configure `backend/pyproject.toml` with `uv`, Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, asyncpg, pgvector, pytest, and ruff.
- [x] Create `Makefile` for running linting, formatting, tests, and database migrations.
- [x] Create `.gitignore` covering Python, Node.js, environment variables, and build artifacts.
- [x] **Review Gate 1.1:** Python virtual environment activates cleanly; `uv run pytest` runs with 0 errors.

### Task 1.2: Database Container & Connection Setup
- [x] Define `docker-compose.yml` with PostgreSQL 16 image enabled with `pgvector` extension.
- [x] Implement `backend/spindle/config.py` using Pydantic `BaseSettings` for environment variables.
- [x] Implement `backend/spindle/database.py` with SQLAlchemy 2.0 async engine and sessionmaker.
- [x] Initialize Alembic with async configuration (`alembic/env.py`).
- [x] **Review Gate 1.2:** Database starts in Docker, test connection succeeds, and pgvector extension is verified.

### Task 1.3: Core Relational Data Models & Initial Migration
- [x] Implement base model and mixins (`UUIDBaseModel`, `TimestampMixin`).
- [x] Implement models in `backend/spindle/models/`:
  - [x] `project.py`: Project
  - [x] `document.py`: SourceDocument, DocumentExcerpt
  - [x] `entity.py`: Character, Location, WorldRule, Relationship
  - [x] `event.py`: Event, NarrativeThread
  - [x] `knowledge.py`: CharacterKnowledge
  - [x] `constraint.py`: Constraint
  - [x] `suggestion.py`: Suggestion, SuggestionRevision, NarrativeBranch
- [x] Generate and apply baseline Alembic migration script.
- [x] **Review Gate 1.3:** Migrations apply cleanly to PostgreSQL; test fixtures can insert and query each model.

### Task 1.4: FastAPI Application Foundation & Health Endpoint
- [x] Implement FastAPI application factory in `backend/spindle/api/app.py`.
- [x] Add CORS middleware and global exception handling.
- [x] Implement `/health` and `/api/v1/health` endpoints returning database connectivity status.
- [x] Write integration test verifying FastAPI test client against the health endpoint.
- [x] **Review Gate 1.4:** `pytest backend/tests/integration/test_health.py` passes.

---

## Stage 2: Story Ingestion & Provenance Pipeline

### Task 2.1: Markdown & Frontmatter Parser
- [x] Implement `backend/spindle/ingestion/parser.py` using `python-frontmatter` / AST parser.
- [x] Extract YAML frontmatter properties (`type`, `role`, `when`, `order`, `summary`, etc.).
- [x] Implement `wikilinks.py` to extract Obsidian links (`[[Target]]`, `[[Target|Alias]]`).
- [x] Implement Markdown section chunking preserving heading hierarchies (`## Concept`, `## Psychology`).
- [x] Unit tests for parsing character, event, and scene markdown files.
- [x] **Review Gate 2.1:** Parser extracts structured attributes and wiki-links from sample notes with 100% test coverage.

### Task 2.2: Content Hashing & Incremental Sync Engine
- [x] Implement `backend/spindle/ingestion/hasher.py` for SHA-256 calculation.
- [x] Implement change detection comparing vault file hashes against `SourceDocument.content_hash`.
- [x] Support handling updated, deleted, and renamed files.
- [x] **Review Gate 2.2:** Unit tests verify that unchanged files are skipped, edited files are re-indexed, and deleted files are tracked.

### Task 2.3: Entity Extraction & Reference Resolution
- [x] Implement `backend/spindle/ingestion/resolver.py` to map Obsidian note titles and aliases to stable Entity UUIDs.
- [x] Extract Characters, Events, Locations, and World Rules into relational models.
- [x] Record source provenance (source document ID, file path, line numbers/excerpts, extraction confidence).
- [x] Distinguish auto-extracted facts from author-confirmed facts (`canon_status`).
- [x] **Review Gate 2.3:** End-to-end ingestion test parses sample vault files and populates database with correct relationships and provenance.

### Task 2.4: Vault Sync & Narrative Query REST API Endpoints
- [x] Implement concise, narrative-aligned REST routes with `X-Project-ID` header (or query param) context:
  - [x] `POST /api/v1/vault/sync`: Accept batch file payloads or trigger vault sync.
  - [x] `GET /api/v1/vault/status`: Monitor sync state, indexing progress, and error counts.
  - [x] `GET /api/v1/entities`: Filter and list extracted entities (characters, events, locations, rules).
  - [x] `GET /api/v1/story/overview`: Return high-level narrative metrics for Obsidian side panel.
  - [x] `GET /api/v1/documents`: List indexed source files and hashes.
- [x] **Review Gate 2.4:** API integration tests verify vault sync payload processing, status tracking, and entity retrieval.

---

## Stage 3: Narrative State Service & Constraint Engine

### Task 3.1: Narrative State Service
- [x] Implement `backend/spindle/core/state_service.py` with `get_story_state(project_id, narrative_position, branch_id)`.
- [x] Decouple `narrative_position` (manuscript order) from chronological timeline `order`.
- [x] Assemble point-in-time state: characters, established events, active world rules, active constraints, and open narrative threads.
- [x] **Review Gate 3.1:** Unit tests verify correct narrative state snapshot generation at varying scene positions.

### Task 3.2: Character Epistemic (Knowledge) Ledger
- [x] Implement epistemic state query in `backend/spindle/core/knowledge.py`.
- [x] Track knowledge status: `UNKNOWN`, `SUSPECTED`, `BELIEVED`, `CONFIRMED`, `FALSE_BELIEF`, `CONCEALED`.
- [x] Validate what a character knows at a specific narrative event.
- [x] **Review Gate 3.2:** Unit tests verify epistemic status transitions and prevent anachronistic knowledge leakage.

### Task 3.3: Centralized Constraint Engine & Deterministic Validators
- [x] Implement `backend/spindle/core/constraints/engine.py` supporting `PASS`, `FAIL`, `WARNING`, `INSUFFICIENT_CONTEXT`.
- [x] Implement deterministic validators in `backend/spindle/core/constraints/deterministic/`:
  - [x] `chronology.py`: Temporal ordering and causality validator (precondition must precede event).
  - [x] `life_status.py`: Character life/death availability checker.
  - [x] `epistemic.py`: Character knowledge boundary validator.
  - [x] `world_rule.py`: Hard world rule limit checker.
- [x] Return structured `ValidationReport` with rule IDs, outcomes, and failure rationale.
- [x] **Review Gate 3.3:** Unit tests verify that hard constraint violations immediately trigger `FAIL` with descriptive diagnostic output.

---

## Stage 4: Multi-Agent Workflow with LangGraph

### Task 4.1: Provider-Independent LLM Interface & Prompt Registry
- [x] Implement `backend/spindle/llm/client.py` abstract interface.
- [x] Implement `MockLLMClient` with deterministic rule-based output for automated tests.
- [x] Implement production LLM client (supporting OpenAI, Anthropic, Gemini / LiteLLM) with retry and timeout policies.
- [x] Centralize prompt templates in `backend/spindle/llm/prompts.py`.
- [x] **Review Gate 4.1:** Test suite runs against `MockLLMClient` with zero network dependency.

### Task 4.2: LangGraph State & Agent Node Implementation
- [x] Define `GraphState` TypedDict in `backend/spindle/agents/state.py`.
- [x] Implement individual agent nodes:
  - [x] `NarrativeDirectorNode`: Request classification & scope.
  - [x] `CanonAnalystNode`: Canon retrieval & thread identification.
  - [x] `CharacterAnalystNode`: Motives, relationships & behavioral plausibility.
  - [x] `TimelineAnalystNode`: Temporal ordering & presence checks.
  - [x] `CausalReasonerNode`: Causal dependencies & consequences.
  - [x] `PlotArchitectNode`: Suggestion generation (Plot point, Side story, Continuity).
  - [x] `ConstraintValidatorNode`: Invokes Constraint Engine.
  - [x] `NarrativeCriticNode`: Originality, plausibility, and value scoring.
  - [x] `ResultSynthesizerNode`: Compiles final suggestion payload.
- [x] **Review Gate 4.2:** Each node is independently unit tested with mocked state inputs.

### Task 4.3: Graph Compilation, Routing & Bounded Revisions
- [x] Assemble LangGraph workflow in `backend/spindle/agents/graph.py`.
- [x] Implement parallel fan-out for Character, Timeline, and Causal analysis.
- [x] Implement conditional router: if hard constraint fails, route back to Plot Architect with revision hints (max 2 iterations).
- [x] Ensure non-destructive output and human-approval interrupt state.
- [x] **Review Gate 4.3:** End-to-end graph test verifies successful plot generation and constraint-triggered revision loop.

### Task 4.4: Narrative Generation REST API Endpoints
- [x] Implement concise generation routes with `X-Project-ID` header (or query param) context:
  - [x] `POST /api/v1/generate/plot-point`: Generate contextually grounded, constraint-checked plot points.
  - [x] `POST /api/v1/generate/side-story`: Generate canon-consistent side stories with beginning, development, and resolution.
  - [x] `POST /api/v1/generate/continuity-analysis`: Check narrative state for potential continuity contradictions.
  - [x] `GET /api/v1/suggestions/{suggestion_id}`: Retrieve suggestion details, assumptions, evidence, and validation reports.
  - [x] `GET /api/v1/suggestions`: List suggestions filtered by `approval_status` or `suggestion_type`.
- [x] **Review Gate 4.4:** API integration tests verify asynchronous generation and retrieval of suggestions with validation reports.

---

## Stage 5: Suggestion Review, Approval & Canon Commitment

### Task 5.1: Suggestion Lifecycle Management
- [ ] Implement state machine: `GENERATED` -> `VALIDATING` -> `VALIDATED/REJECTED` -> `PENDING_AUTHOR_APPROVAL` -> `APPROVED/REJECTED/EDITED` -> `COMMITTED`.
- [ ] Implement endpoints:
  - [ ] `POST /api/v1/suggestions/{id}/approve`
  - [ ] `POST /api/v1/suggestions/{id}/reject` (with mandatory reason)
  - [ ] `PUT /api/v1/suggestions/{id}/edit`
  - [ ] `POST /api/v1/suggestions/{id}/commit`
- [ ] **Review Gate 5.1:** Tests verify approval lifecycle and guard against unapproved canon modifications.

### Task 5.2: Non-Destructive Canon Commit Service
- [ ] Implement commit service: writes approved suggestion as a new markdown document or structured insertion artifact.
- [ ] Maintain audit log linking committed document to original suggestion and author edits.
- [ ] Update narrative state database with confirmed canon entities.
- [ ] **Review Gate 5.2:** Tests confirm existing files remain untouched while new story files are cleanly integrated into the indexed narrative state.

---

## Stage 6: Obsidian Plugin Implementation

### Task 6.1: Plugin Scaffold & Backend Client
- [ ] Initialize TypeScript Obsidian plugin project in `obsidian-plugin/` with `esbuild`.
- [ ] Implement typed API client (`backendClient.ts`) for all Spindle endpoints.
- [ ] Implement Settings tab (backend URL, project ID, connection test).
- [ ] **Review Gate 6.1:** Plugin loads in Obsidian, connects to backend `/health`, and displays connection status.

### Task 6.2: Vault Synchronization Interface
- [ ] Implement local vault scanner reading frontmatter, wiki-links, and markdown files.
- [ ] Build Sync command in Obsidian to push changed files to backend.
- [ ] Display sync status, last indexed timestamp, and error reporting.
- [ ] **Review Gate 6.2:** Syncing a sample vault populates the backend database from within Obsidian.

### Task 6.3: Story Overview & Generation UI
- [ ] Implement `StoryOverviewView` side-panel displaying:
  - Character count, Event count, Location count, Active constraints, Unresolved threads.
- [ ] Implement `GenerateModal` allowing free-form author prompt and mode selection (Plot Point, Side Story, Continuity).
- [ ] **Review Gate 6.3:** Author can view story metrics and trigger a generation request directly from Obsidian.

### Task 6.4: Suggestion Review & Canon Commitment Modal
- [ ] Implement `SuggestionReviewModal`:
  - Displays generated proposal, premise, and narrative reasoning.
  - Highlights supporting source citations.
  - Displays Constraint Validation Report (pass/fail/warning tags).
  - Action buttons: Approve, Edit, Reject (with reason), and Commit to Vault.
- [ ] Ensure committed suggestions write safely to designated vault path without altering existing manuscripts.
- [ ] **Review Gate 6.4:** Author can review suggestion, inspect validation warnings, approve, and commit a new markdown note to the vault.

---

## Stage 7: Web Application (Monorepo)

### Task 7.1: Web App Scaffold & Dashboard
- [ ] Initialize Next.js / React application in `web/`.
- [ ] Implement typed API client connecting to Spindle backend.
- [ ] Build Project Overview page showing narrative graph, characters, timeline, and constraints.
- [ ] Build Suggestion Explorer & Validation Inspector.
- [ ] **Review Gate 7.1:** Web dashboard visualizes project narrative state and allows reviewing suggestions.

---

## Stage 8: Comprehensive Narrative Evaluation & Hardening

### Task 8.1: Synthetic Narrative Test Suite (7 Core Scenarios)
- [ ] Scenario 1: Character acting on unlearned knowledge (Must fail epistemic constraint).
- [ ] Scenario 2: Deceased character appearing in later scene without explanation (Must fail life-status constraint).
- [ ] Scenario 3: Event occurring prior to its causal prerequisite (Must fail temporal constraint).
- [ ] Scenario 4: Magic/world rule violation (Must fail world-rule constraint).
- [ ] Scenario 5: Side story contradicting established canon (Must fail canon consistency check).
- [ ] Scenario 6: Unexpected character behavior with plausible motivation (Must issue warning, not hard failure).
- [ ] Scenario 7: Alternate timeline exploration (Must verify branch isolation from main canon).
- [ ] **Review Gate 8.1:** All 7 synthetic scenarios pass with 100% deterministic test assertion reliability.

### Task 8.2: Documentation & Local Setup Verification
- [ ] Comprehensive `README.md` with step-by-step setup for backend, obsidian-plugin, and web app.
- [ ] Document Docker workflow, environment variables, and migration instructions.
- [ ] **Review Gate 8.2:** Clean local setup test runs from scratch without missing dependencies or broken links.

