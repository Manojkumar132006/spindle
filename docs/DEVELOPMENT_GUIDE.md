# Spindle Developer & Setup Guide

This guide walks through setting up, developing, testing, and debugging the Spindle backend and Obsidian plugin.

---

## 1. Prerequisites

- **macOS / Linux**
- **Docker & Docker Compose** (for PostgreSQL 16 + pgvector)
- **Python 3.12+**
- **`uv`**: Fast Python package manager (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js 18+ and npm**

---

## 2. Environment Setup

### 1. Database (PostgreSQL 16 with pgvector)
Run the database in the background:
```bash
docker compose up -d
```
Verify the container is healthy:
```bash
docker ps --filter "name=spindle-postgres"
```

Connection details (default in `backend/.env`):
```env
DATABASE_URL=postgresql+asyncpg://spindle_user:spindle_password@localhost:5432/spindle_db
```

### 2. Backend Dependencies & Migrations
```bash
cd backend

# Install dependencies into .venv
uv sync

# Run database migrations
uv run alembic upgrade head
```

### 3. LLM API Key Configuration
Configure your Gemini API key in `backend/.env`:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```
*(OpenAI is also supported by setting `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...`)*

---

## 3. Running the Backend Server

Start FastAPI with hot reload:
```bash
cd backend
uv run uvicorn spindle.api.app:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 4. Building the Obsidian Plugin

Navigate to `obsidian-plugin/`:
```bash
cd obsidian-plugin

# Install dependencies
npm install

# Typecheck with TypeScript
./node_modules/.bin/tsc --noEmit

# Run unit tests
node --import tsx --test tests/*.test.ts

# Build production bundle (generates main.js and styles.css)
node esbuild.config.mjs production
```

### Linking to a Live Obsidian Vault
To test directly in Obsidian:
```bash
# Symlink the plugin folder into your vault's .obsidian/plugins/
ln -s "/path/to/spindle/obsidian-plugin" "/path/to/YourVault/.obsidian/plugins/spindle-narrative"
```
In Obsidian:
1. Open **Settings** > **Community plugins**.
2. Click **Reload plugins**.
3. Enable **Spindle Narrative Intelligence**.

---

## 5. Running the Automated Test Suites

### Backend Tests (pytest)
```bash
cd backend
.venv/bin/pytest -v
```
All 53 unit and integration tests run in under 1 second.

### Code Formatting & Linting (ruff)
```bash
cd backend
.venv/bin/ruff check .
.venv/bin/ruff format . --check
```

### Frontend Tests (Node.js test runner)
```bash
cd obsidian-plugin
node --import tsx --test tests/*.test.ts
```
Verifies backend client calls, vault scanner change detection, and vault scaffolder folder/template creation.

---

## 6. Troubleshooting Common Issues

### 1. Database Connection Refused
If `curl http://localhost:8000/health` reports database errors:
```bash
# Ensure Docker is running and restart container
docker compose restart spindle-postgres
```

### 2. Hallucinated Characters in Suggestions
- Ensure you have clicked **"Sync Vault"** in the Story Overview pane.
- The `EntityExistenceValidator` strictly checks proposals against characters established in your vault.
- Orphaned ghost entities from older test sessions are automatically pruned during sync.

### 3. Templater Templates Not Triggering
- Click **"📁 Scaffold Vault Structure"** in Spindle settings or run `Spindle: Scaffold Story Vault Structure & Templates`.
- Verify that `.obsidian/plugins/templater-obsidian/data.json` contains `"trigger_on_file_creation_mode": "folder"`.
