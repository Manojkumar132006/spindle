# Spindle Documentation Index

Welcome to the comprehensive documentation for **Spindle**, the constraint-driven narrative intelligence system for fiction authors.

Each major subsystem has a dedicated, in-depth documentation guide:

---

## 📚 Documentation Directory

| Document | Description | Key Topics |
| :--- | :--- | :--- |
| [**Architecture & Design**](ARCHITECTURE.md) | High-level system architecture and logical layers | Interface layer, API layer, LangGraph engine, PostgreSQL/pgvector |
| [**API Reference**](API_REFERENCE.md) | Complete REST API specification for all endpoints | `/vault/sync`, `/story/overview`, `/generate/*`, `/suggestions/*` |
| [**Multi-Agent LangGraph Workflow**](MULTI_AGENT_WORKFLOW.md) | 8-agent cognitive pipeline and state graph | Narrative Director, Canon Analyst, Plot Architect, self-correction loop |
| [**Constraint Engine & Validators**](CONSTRAINT_ENGINE.md) | Deterministic Python verification logic | `EntityExistenceValidator`, `LifeStatusValidator`, `EpistemicValidator`, rules |
| [**Vault Ingestion & Sync Engine**](VAULT_INGESTION.md) | Incremental Obsidian Markdown indexing | Frontmatter parsing, Wikilinks, SHA-256 change detection, ghost pruning |
| [**Autonomous Branch Exploration**](BRANCH_EXPLORATION.md) | Generating divergent storylines without prompts | Dramatic angles (Confrontation, Infiltration, Diplomacy, Retreat), modal UI |
| [**Obsidian Plugin & Templater Guide**](OBSIDIAN_PLUGIN.md) | Desktop writing environment integration | Vault scaffolder, Templater folder triggers, commands, non-destructive commit |
| [**Database Schema & Data Models**](DATABASE_MODELS.md) | PostgreSQL 16 + pgvector relational schema | `Character`, `Event`, `SourceDocument`, `DocumentExcerpt`, `Suggestion` |
| [**Developer & Setup Guide**](DEVELOPMENT_GUIDE.md) | Local environment setup and testing instructions | Docker, FastAPI, `uv`, `pytest`, `ruff`, TypeScript build, troubleshooting |
| [**Task Tracking & Milestones**](TASKS.md) | Implementation roadmap and completion checklist | Phase 1 to Phase 6 progress log |

---

## 🚀 Quick Navigation by Role

- **For Fiction Authors**: Read the [Obsidian Plugin & Templater Guide](OBSIDIAN_PLUGIN.md) and [Autonomous Branch Exploration](BRANCH_EXPLORATION.md) to understand how to write, explore branches, and organize your novel vault.
- **For Backend Developers**: Start with [System Architecture](ARCHITECTURE.md), [Database Models](DATABASE_MODELS.md), and [API Reference](API_REFERENCE.md).
- **For AI / Agent Engineers**: Dive into [Multi-Agent LangGraph Workflow](MULTI_AGENT_WORKFLOW.md) and [Constraint Engine & Validators](CONSTRAINT_ENGINE.md).
