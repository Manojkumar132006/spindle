# Spindle: System Architecture & Design Specification

Spindle is a constraint-driven narrative intelligence system designed for fiction authors. It maintains a structured representation of an author's narrative universe and produces contextually grounded, canon-consistent creative developments without violating established canon or author constraints.

---

## 1. Monorepo Organization

Spindle is structured as a monorepo containing three core applications and shared documentation:

```
spindle/
├── backend/                  # Python 3.12+ FastAPI backend & LangGraph narrative agents
│   ├── spindle/
│   │   ├── api/              # Versioned REST API (v1)
│   │   ├── models/           # SQLAlchemy 2.0 ORM & Pydantic v2 schemas
│   │   ├── core/             # Narrative State Service & Deterministic Constraint Engine
│   │   ├── ingestion/        # Markdown, frontmatter, & Obsidian wikilink parser
│   │   ├── retrieval/        # Hybrid retrieval (Structured SQL + pgvector)
│   │   ├── llm/              # Provider-agnostic LLM interface & prompt registry
│   │   └── agents/           # LangGraph multi-agent workflow
│   ├── alembic/              # Database schema migrations
│   └── tests/                # Unit, integration, and narrative evaluation test suites
├── obsidian-plugin/          # TypeScript Obsidian desktop plugin
│   ├── src/
│   │   ├── api/              # Typed REST client communicating with Spindle backend
│   │   ├── views/            # Native Obsidian views (Overview, Suggestions, Review)
│   │   └── utils/            # Vault file scanner & safe change committer
│   └── manifest.json
├── web/                      # Web dashboard & application interface
│   ├── src/                  # React / Next.js web application
│   └── package.json
├── docs/                     # Architectural specs, API contracts, and task checklists
│   ├── ARCHITECTURE.md
│   ├── TASKS.md
│   └── API_SPEC.md
└── docker-compose.yml        # PostgreSQL 16 + pgvector container
```

---

## 2. Logical Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       INTERFACE LAYER                       │
│      Obsidian Plugin (Desktop)    |    Web Application      │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                          API LAYER                          │
│               FastAPI (Python 3.12+, Async REST)            │
│  - Project Management           - Async Ingestion Status    │
│  - Context Retrieval            - Generation Operations     │
│  - Suggestion Review            - Canon Commitment Gate     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                NARRATIVE INTELLIGENCE LAYER                 │
│                      (LangGraph Engine)                     │
│  - Narrative Director           - Timeline Analyst          │
│  - Canon Analyst                - Causal Reasoner           │
│  - Character Analyst            - Plot Architect            │
│  - Constraint Validator         - Narrative Critic          │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼───────────────┐
│     CONSTRAINT ENGINE       ││   NARRATIVE STATE SERVICE    │
│ - Deterministic Rules       ││ - Point-in-time Story State  │
│ - Epistemic (Knowledge)     ││ - Narrative Pos vs Chronology│
│ - Semantic LLM Checks       ││ - Branch Resolution          │
└──────────────┬──────────────┘└──────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────────────────────▼───────────────┐
│                 PERSISTENCE & RETRIEVAL                     │
│                PostgreSQL 16 + pgvector                     │
│  - Relational Schema (Characters, Events, Constraints, etc.)│
│  - Vector Embeddings (Manuscript Excerpts, Scene Semantics) │
│  - Source Provenance & Audit Trails                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Narrative Data Model

All models use UUID primary keys and track strict provenance back to vault files.

1. **Project:** Multi-story partition; isolates all entities, constraints, and suggestions.
2. **SourceDocument:** Represents ingested markdown files (content hash, path, document type, raw content).
3. **Character:** Name, aliases, role, psychology (values, wound, defenses), trajectory (arc, flaws), metadata.
4. **Event:** Title, narrative position (book/scene order), chronological timestamp, participants, location, causal dependencies, canon status.
5. **Relationship:** Source & target character IDs, type, current state, evolving history.
6. **Location:** Name, kind, region, power structure, narrative role.
7. **WorldRule:** Name, description, rule type (magic, physics, law), enforcement level (hard vs soft).
8. **CharacterKnowledge:** Epistemic ledger tracking what a character knows, suspects, or falsely believes at specific story events.
9. **Constraint:** Explicit author bounds (canon, character behavior, disclosure, world rules) with enforcement method.
10. **NarrativeThread:** Unresolved narrative arcs, plot hooks, introduction and resolution events.
11. **Suggestion:** Generated creative proposal (plot point, side story, continuity resolution), premise, supporting evidence, assumptions, validation report, and approval status.
12. **NarrativeBranch:** Support for hypothetical what-if explorations branching from main canon.

---

## 4. Constraint Engine Architecture

The Constraint Engine is a core differentiator. It evaluates suggestions against existing story state using a two-tier approach:

### Tier 1: Deterministic Rule Checkers
Fast, deterministic Python checks that do not rely on LLM stochasticity:
- **Chronology & Causality:** Ensures an event's preconditions occur before the event itself.
- **Physical Availability / Life Status:** Ensures dead characters do not appear in subsequent scenes without explanation.
- **Epistemic Bounds:** Validates that a character does not act on secrets or information they have not learned by that narrative position.
- **World Rule Violation:** Checks hard limits (e.g. magic costs, spatial constraints).

### Tier 2: Semantic Rule Checkers
LLM-assisted evaluation for subjective nuances:
- Character behavioral plausibility and voice consistency.
- Thematic coherence and tone.

### Validation Outcomes
- `PASS`: Complies fully with constraints.
- `FAIL`: Explicit violation of hard constraint; blocks canon compatibility.
- `WARNING`: Soft constraint or behavioral tension requiring author awareness.
- `INSUFFICIENT_CONTEXT`: Lacking data to confirm consistency (never assumed valid).

---

## 5. LangGraph Multi-Agent Architecture

The generation workflow runs as a directed, bounded LangGraph graph:

1. **Narrative Director:** Classifies incoming request, scopes narrative position and branch.
2. **Context Retrieval:** Queries structured entities and semantic pgvector embeddings.
3. **Canon Analyst:** Identifies active canon, prior precedents, and open threads.
4. **Parallel Analysis Node:**
   - *Character Analyst:* Checks psychological motives and relationships.
   - *Timeline Analyst:* Validates chronological dependencies and scene order.
   - *Causal Reasoner:* Evaluates cause-and-effect chains.
5. **Plot Architect:** Synthesizes analysis into candidate narrative development.
6. **Constraint Validator:** Executes Constraint Engine (Deterministic + Semantic).
7. **Conditional Router:** If hard failure occurs, routes back to Plot Architect with diagnostic feedback (bounded to 2 revisions).
8. **Narrative Critic:** Scores novelty, plausibility, and narrative relevance.
9. **Result Synthesizer:** Compiles structured suggestion, evidence citations, and validation report.
10. **Human Approval Gate:** Suggestion remains in `PENDING_AUTHOR_APPROVAL` until author explicitly approves, edits, or rejects.

---

## 6. Obsidian Plugin & Non-Destructive Canon Commit

- The Obsidian plugin syncs markdown files by calculating local SHA-256 hashes and pushing changes to the backend.
- **Non-Destructive Guarantee:** Spindle never overwrites or edits existing manuscript files without explicit user action.
- When an author commits an approved suggestion:
  - It is written to a designated destination (e.g., `Manuscript/Side Stories/<title>.md` or `Plot/Proposed/<title>.md`).
  - An entry is logged in the project audit history.
  - The backend marks the suggestion as `COMMITTED` and updates the canonical story graph.

