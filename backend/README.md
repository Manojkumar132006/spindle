# Spindle Backend

FastAPI backend, SQLAlchemy 2.0 ORM, PostgreSQL + pgvector storage, deterministic constraint validation engine, and 8-agent LangGraph narrative orchestration.

---

## Architecture Overview

- **`spindle/ingestion/`**: Markdown frontmatter parser, bidirectional `[[WikiLinks]]` extraction, SHA-256 content hashing, entity resolution, and vault synchronization.
- **`spindle/core/constraints/`**: Deterministic validation engine with 4 core validators:
  - `ChronologyValidator`: Validates non-negative temporal intervals, event sequencing, and causal prerequisites.
  - `LifeStatusValidator`: Enforces character mortality and life status consistency.
  - `EpistemicValidator`: Verifies character presence and information discovery prerequisites.
  - `WorldRuleValidator`: Validates magic system rules, world limits, and author directives.
- **`spindle/agents/`**: 8-agent LangGraph workflow:
  - `Director` -> `CanonAnalyst` -> `CharacterAnalyst` -> `TimelineAnalyst` -> `CausalReasoner` -> `PlotArchitect` -> `ConstraintValidator` -> `NarrativeCritic` -> `ResultSynthesizer`.
  - Conditional revision loop: routes back to `PlotArchitect` on hard constraint failure (max 2 iterations).
- **`spindle/core/lifecycle.py` & `commit_service.py`**: State machine enforcing author approval transitions and non-destructive file commitment to Obsidian vaults.
- **`spindle/api/v1/`**: Clean REST routes (`/vault/sync`, `/vault/status`, `/story/overview`, `/generate/*`, `/suggestions/*`) with project context resolved via `X-Project-ID` header.

---

## Local Setup & Development

### 1. Requirements

- Python 3.12+
- `uv` package manager (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker (for PostgreSQL + pgvector)

### 2. Database & Migrations

```bash
# Start PostgreSQL container from repository root:
docker compose up -d

# Install dependencies and sync virtual environment:
uv sync

# Run database migrations:
uv run alembic upgrade head
```

### 3. Running the Server

```bash
# Start FastAPI with live reload:
uv run uvicorn spindle.api.app:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health check: `curl http://localhost:8000/health`

### 4. Running Tests

```bash
# Run full pytest suite (50 tests):
uv run pytest

# Run with test coverage:
uv run pytest --cov=spindle tests/
```
