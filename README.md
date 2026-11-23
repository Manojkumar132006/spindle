# Spindle

**Constraint-Driven Narrative Intelligence System**

Spindle is an author-centric narrative intelligence system designed for fiction writers. It ingests Obsidian story vaults, builds a structured narrative knowledge graph with source provenance, and produces canon-compatible plot points, side stories, and continuity analyses strictly bounded by author-defined constraints.

---

## Key Principles

- **Canon Preservation:** Existing manuscript prose is untampered with. The system is non-destructive.
- **Strict Constraint Adherence:** Hard constraints (chronology, character mortality, epistemic bounds, magic rules) are evaluated by deterministic logic.
- **Traceable Narrative Reasoning:** Every suggestion cites supporting evidence, assumptions, and a full constraint validation report.
- **Human in the Loop:** The author has absolute veto power. No AI-generated proposal becomes canon without explicit human approval.

---

## Monorepo Layout

- [`backend/`](./backend): Python 3.12+ FastAPI backend, SQLAlchemy 2.0 ORM, PostgreSQL + pgvector, and LangGraph multi-agent orchestration.
- [`obsidian-plugin/`](./obsidian-plugin): Native TypeScript Obsidian desktop plugin providing vault synchronization, story metrics, and suggestion review/approval UI.
- [`web/`](./web): Web application and dashboard for visual narrative state exploration and review.
- [`docs/`](./docs): Documentation, architectural specifications, and task checklists.
  - [Architecture Specification](docs/ARCHITECTURE.md)
  - [Master Task Checklist](docs/TASKS.md)

---

## Development & Roadmap

Development is broken into granular, reviewable tasks. Please refer to [docs/TASKS.md](docs/TASKS.md) for the complete implementation checklist and review gates.

