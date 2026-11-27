# Spindle

**Constraint-Driven Narrative Intelligence System for Fiction Authors**

Spindle is an author-centric narrative intelligence system designed for fiction authors. It integrates directly with Obsidian vaults, builds a structured narrative knowledge graph with source provenance, and produces canon-compatible plot points, side stories, and continuity analyses strictly bounded by author-defined constraints.

---

## Key Principles & System Guarantees

- **Non-Destructive Canon Preservation:** Existing manuscript prose is never modified or overwritten. Approved suggestions are committed as separate, dedicated notes with non-colliding file paths.
- **Deterministic Constraint Enforcement:** Hard constraints (chronology, character mortality, epistemic bounds, magic/world rules) are evaluated by deterministic Python validators, never left to LLM hallucination.
- **Traceable Narrative Reasoning:** Every suggestion cites supporting evidence from your vault, transparent assumptions, and a full constraint validation report.
- **Strict Human-in-the-Loop:** The author maintains absolute veto power. No AI-generated proposal becomes canon without explicit author review and commitment.

---

## Documentation

Comprehensive guides for every subsystem are located in [`docs/`](docs/README.md):

- 📖 [**System Architecture & Design**](docs/ARCHITECTURE.md): Full logical layer overview and dataflow.
- ⚡ [**REST API Reference**](docs/API_REFERENCE.md): Complete specification of all backend endpoints.
- 🤖 [**Multi-Agent LangGraph Workflow**](docs/MULTI_AGENT_WORKFLOW.md): Detailed 8-agent cognitive pipeline.
- 🛡️ [**Constraint Engine & Validators**](docs/CONSTRAINT_ENGINE.md): Deterministic rules, hallucination guards, and reports.
- 📂 [**Vault Ingestion & Sync Engine**](docs/VAULT_INGESTION.md): Markdown AST, Wikilinks, SHA-256 change detection, ghost pruning.
- 🌿 [**Autonomous Branch Exploration**](docs/BRANCH_EXPLORATION.md): Discovering divergent storylines without prompts.
- 🔌 [**Obsidian Plugin & Templater Guide**](docs/OBSIDIAN_PLUGIN.md): Desktop plugin, vault scaffolder, and Templater setup.
- 🗄️ [**Database Schema & Data Models**](docs/DATABASE_MODELS.md): PostgreSQL 16 + pgvector relational schema.
- 🛠️ [**Developer & Setup Guide**](docs/DEVELOPMENT_GUIDE.md): Local environment setup, test execution, and debugging.
- 📋 [**Task Tracking Roadmap**](docs/TASKS.md): Implementation milestone log.

---

## Monorepo Layout

```
spindle/
├── backend/            # Python 3.12+ FastAPI backend & LangGraph multi-agent engine
│   ├── alembic/        # PostgreSQL schema migrations
│   ├── spindle/        # Core application source code
│   │   ├── agents/     # 8-agent LangGraph workflow
│   │   ├── api/        # REST API endpoints (/vault, /story, /generate, /suggestions)
│   │   ├── core/       # Constraint engine, lifecycle guards, canon commit service
│   │   ├── ingestion/  # Obsidian markdown parser, wikilinks, hashing, sync service
│   │   ├── llm/        # Multi-provider LLM client with MockLLM fallback
│   │   └── models/     # SQLAlchemy 2.0 ORM models with pgvector support
│   └── tests/          # Comprehensive unit and integration test suite (50 tests)
├── obsidian-plugin/    # Native TypeScript Obsidian desktop plugin
│   ├── src/            # Plugin lifecycle, backend client, scanner, views, modals
│   ├── styles.css      # Native Obsidian theme styling
│   └── tests/          # Component unit tests with tsx test runner
├── web/                # Future web dashboard (Monorepo placeholder)
├── docs/               # Architecture specifications and task tracking
└── docker-compose.yml  # PostgreSQL 16 + pgvector container
```

---

## Prerequisites

Before running Spindle, ensure you have the following installed on your machine:

1. **Docker & Docker Compose** (for PostgreSQL 16 + pgvector)
2. **Python 3.12+**
3. **`uv`** (fast Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)
4. **Node.js 18+ & npm** (for building the Obsidian plugin)

---

## Step-by-Step Running Guide

### 1. Start the Database (PostgreSQL + pgvector)

Start the PostgreSQL 16 container with `pgvector` pre-configured:

```bash
docker compose up -d
```

Verify that the database is healthy:

```bash
docker ps
# Status should indicate: Up ... (healthy) ... 0.0.0.0:5432->5432/tcp (spindle-postgres)
```

*(To stop the database later: `docker compose down`)*

---

### 2. Configure & Migrate the Backend

Navigate to the `backend/` directory, install all Python dependencies, and run database migrations:

```bash
cd backend

# Install all backend dependencies (FastAPI, SQLAlchemy, LangGraph, pytest, ruff)
uv sync

# Run Alembic migrations to create tables and vector indexes
uv run alembic upgrade head
```

---

### 3. Run the Backend API Server

Start the FastAPI backend with hot-reload enabled:

```bash
# Using Makefile from root:
make dev

# OR directly with uv from backend/:
cd backend
uv run uvicorn spindle.api.app:app --reload --host 0.0.0.0 --port 8000
```

Once running, verify the backend health endpoint:

```bash
curl http://localhost:8000/health
# Response: {"status":"ok","project":"Spindle","version":"0.1.0","environment":"development"}
```

- **Interactive API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Documentation (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 4. Build the Obsidian Plugin

In a new terminal window, navigate to `obsidian-plugin/`, install dependencies, run tests, and compile the bundle:

```bash
cd obsidian-plugin

# Install Node dependencies
npm install

# Run TypeScript typechecks and unit tests
npm run typecheck
npm test

# Build production bundle with esbuild (creates main.js)
npm run build
```

The build process produces `main.js`, `manifest.json`, and uses `styles.css`.

---

### 5. Install & Run in Obsidian

To load the Spindle plugin into your local Obsidian story vault:

1. Locate your Obsidian vault directory (e.g., `~/Documents/MyStoryVault/`).
2. Inside your vault, ensure the `.obsidian/plugins/` directory exists:
   ```bash
   mkdir -p ~/Documents/MyStoryVault/.obsidian/plugins/spindle-narrative
   ```
3. Copy or symlink the build files into the plugin directory:
   ```bash
   # Option A: Symlink for active development (recommended)
   ln -s "$(pwd)/obsidian-plugin" ~/Documents/MyStoryVault/.obsidian/plugins/spindle-narrative

   # Option B: Copy files directly
   cp obsidian-plugin/main.js obsidian-plugin/manifest.json obsidian-plugin/styles.css ~/Documents/MyStoryVault/.obsidian/plugins/spindle-narrative/
   ```
4. Open **Obsidian**:
   - Go to **Settings** (`Cmd + ,` or `Ctrl + ,`) -> **Community plugins**.
   - Toggle **Restricted mode** to **Off**.
   - In "Installed plugins", find **Spindle Narrative Intelligence** and toggle it **On**.
5. Configure the Plugin:
   - Go to **Settings** -> **Spindle**.
   - Ensure Backend API URL is set to `http://localhost:8000`.
   - Click **Test Connection** (should display `✓ Connected`).
   - *(Optional)* Provide an existing Project ID or leave empty to automatically initialize the default project workspace.

---

### 6. End-to-End Workflow in Obsidian

1. **Vault Synchronization:**
   - Open Obsidian Command Palette (`Cmd + P` or `Ctrl + P`).
   - Run: `Spindle: Sync Vault to Backend`.
   - The plugin scans your markdown notes, parses frontmatter and `[[WikiLinks]]`, and indexes characters, events, and world rules into the backend database.
2. **Story Overview Side Pane:**
   - Click the **Book Open** icon on the left ribbon, or run command `Spindle: Open Story Overview`.
   - Inspect live narrative metrics: Character count, Chronological Events, Locations, Active Constraints, and Open Threads.
3. **Generate Narrative Proposals:**
   - Click **Generate with AI** in the side pane or run `Spindle: Generate with AI`.
   - Choose your generation mode:
     - **Plot Point:** Contextually grounded scene continuation.
     - **Side Story:** Standalone vignette expanding character arcs.
     - **Continuity Analysis:** Audit character knowledge and temporal prerequisites.
   - Enter your prompt, specify narrative position (e.g. `2.0`), and select involved characters.
   - Click **Generate Suggestion**.
4. **Review, Inspect Constraints & Commit:**
   - The **Suggestion Review Modal** opens automatically.
   - Review proposed scene beats, supporting canon sources, and the **Constraint Validation Report** (Pass/Fail/Warning badges).
   - Choose your author action:
     - **Approve:** Endorses suggestion for inclusion.
     - **Edit:** Refine title, premise, or scene beats with revision tracking.
     - **Reject:** Log reason for rejection.
     - **Commit to Vault Canon:** Writes the proposal safely as a new Markdown file into your vault (`Manuscript/Side Stories/...`) without modifying existing files, and links it to confirmed story canon.

---

## Running Automated Tests

Spindle maintains 100% test pass rates across all modules:

### Backend Tests (Pytest)

```bash
cd backend
uv run pytest
```
*Executes all 50 unit and integration tests (PostgreSQL integration, vault ingestion, deterministic constraint engine, LangGraph agent workflows, suggestion lifecycle, and canon commit service).*

### Obsidian Plugin Tests (Node Test Runner + tsx)

```bash
cd obsidian-plugin
npm test
```
*Executes typed unit tests verifying backend client headers, URL routing, error handling, and vault scanner exclusion filtering.*

---

## Root Makefile Commands

| Command | Description |
|---|---|
| `make db-up` | Start PostgreSQL 16 + pgvector container |
| `make db-down` | Stop PostgreSQL container |
| `make migrate` | Apply Alembic database migrations |
| `make dev` | Start FastAPI backend server with hot-reload |
| `make test` | Run backend test suite |
| `make format` | Format backend code using `ruff format` |
| `make lint` | Lint backend code using `ruff check` |
