# Multi-stage build for Spindle Backend
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies without installing root project
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and migrations
COPY spindle/ ./spindle/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Final project installation
RUN uv sync --frozen --no-dev

# Production runtime stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and project from builder
COPY --from=builder /app /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

# Health check using FastAPI root health endpoint
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn
CMD ["uvicorn", "spindle.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

