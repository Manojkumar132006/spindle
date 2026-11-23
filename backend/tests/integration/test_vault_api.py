"""Integration tests for vault synchronization and narrative query API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from spindle.api.app import app
from spindle.database import get_db_session
from spindle.models.project import Project


@pytest.fixture
def override_db_session(test_session):
    """Override get_db_session FastAPI dependency with test_session."""

    async def _override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_vault_api_lifecycle(override_db_session, test_session):
    """Test full API sync, entity inspection, story overview, and document retrieval."""
    # Create test project
    project = Project(
        name="API Test Chronicles",
        description="Universe for testing concise REST API routes.",
    )
    test_session.add(project)
    await test_session.commit()

    headers = {"X-Project-ID": str(project.id)}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/v1/vault/sync - Initial batch sync
        sync_payload = {
            "files": [
                {
                    "path": "Characters/Elena Vareth.md",
                    "content": (
                        "---\ntype: character\nrole: protagonist\naliases: [the scribe]\n---\n"
                        "## Concept\nA scribe who discovers the truth.\n"
                    ),
                },
                {
                    "path": "Worldbuilding/Locations/Varenhold.md",
                    "content": (
                        "---\ntype: location\nkind: city\n---\n"
                        "## What a visitor notices first\nToll gates on every bridge.\n"
                    ),
                },
                {
                    "path": "Worldbuilding/Magic/The Binding Oath.md",
                    "content": ("---\ntype: magic\n---\n## Effect\nForces absolute obedience.\n"),
                },
            ]
        }

        sync_resp = await client.post("/api/v1/vault/sync", json=sync_payload, headers=headers)
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["status"] == "success"
        assert sync_data["total_files"] == 3
        assert sync_data["indexed_files"] == 3
        assert sync_data["extracted_characters"] == 1
        assert sync_data["extracted_locations"] == 1
        assert sync_data["extracted_rules"] == 1

        # 2. GET /api/v1/vault/status
        status_resp = await client.get("/api/v1/vault/status", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["total_documents"] == 3
        assert status_data["project_name"] == "API Test Chronicles"
        assert status_data["last_synced_at"] is not None

        # 3. GET /api/v1/story/overview
        overview_resp = await client.get("/api/v1/story/overview", headers=headers)
        assert overview_resp.status_code == 200
        overview_data = overview_resp.json()
        assert overview_data["characters_count"] == 1
        assert overview_data["locations_count"] == 1
        assert overview_data["world_rules_count"] == 1
        assert overview_data["documents_count"] == 3

        # 4. GET /api/v1/entities
        entities_resp = await client.get("/api/v1/entities", headers=headers)
        assert entities_resp.status_code == 200
        entities_data = entities_resp.json()
        assert len(entities_data["characters"]) == 1
        char_item = entities_data["characters"][0]
        assert char_item["name"] == "Elena Vareth"
        assert "the scribe" in char_item["aliases"]

        # 5. GET /api/v1/entities/{entity_id}
        char_id = char_item["id"]
        single_entity_resp = await client.get(f"/api/v1/entities/{char_id}", headers=headers)
        assert single_entity_resp.status_code == 200
        single_char = single_entity_resp.json()
        assert single_char["name"] == "Elena Vareth"
        assert single_char["entity_type"] == "character"

        # 6. GET /api/v1/documents
        docs_resp = await client.get("/api/v1/documents", headers=headers)
        assert docs_resp.status_code == 200
        docs_data = docs_resp.json()
        assert len(docs_data) == 3
        first_doc = docs_data[0]

        # 7. GET /api/v1/documents/{doc_id}
        doc_detail_resp = await client.get(f"/api/v1/documents/{first_doc['id']}", headers=headers)
        assert doc_detail_resp.status_code == 200
        doc_detail = doc_detail_resp.json()
        assert "file_path" in doc_detail
        assert "raw_content" in doc_detail
        assert "excerpts" in doc_detail

        # 8. POST /api/v1/vault/sync - Second sync with unchanged content -> skipped
        sync_resp_2 = await client.post("/api/v1/vault/sync", json=sync_payload, headers=headers)
        assert sync_resp_2.status_code == 200
        sync_data_2 = sync_resp_2.json()
        assert sync_data_2["skipped_files"] == 3
        assert sync_data_2["indexed_files"] == 0
