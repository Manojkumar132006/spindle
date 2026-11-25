"""Integration tests for narrative generation and suggestion API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from spindle.api.app import app
from spindle.database import get_db_session
from spindle.models.project import Project
from tests.unit.test_agents import FakeTestLLMClient


@pytest.fixture(autouse=True)
def mock_llm_for_integration(monkeypatch):
    """Stub LLM client for offline integration tests."""
    monkeypatch.setattr("spindle.api.v1.generate.get_llm_client", lambda: FakeTestLLMClient())


@pytest.fixture
def override_db_session(test_session):
    """Override get_db_session FastAPI dependency with test_session."""

    async def _override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_generate_plot_point_and_suggestions_api(override_db_session, test_session):
    """Test POST /api/v1/generate/plot-point and suggestion query endpoints."""
    project = Project(
        name="Generation API World",
        description="Testing generation endpoints.",
    )
    test_session.add(project)
    await test_session.commit()

    headers = {"X-Project-ID": str(project.id)}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/v1/generate/plot-point
        payload = {
            "request": "Elena investigates the council archive late at night.",
            "narrative_position": 7.0,
        }
        resp = await client.post("/api/v1/generate/plot-point", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "id" in data
        assert data["project_id"] == str(project.id)
        assert data["suggestion_type"] == "plot_point"
        assert len(data["title"]) > 0
        assert len(data["premise"]) > 0
        assert data["approval_status"] == "pending_author_approval"
        assert "validation_results" in data
        suggestion_id = data["id"]

        # 2. POST /api/v1/generate/side-story
        side_payload = {
            "request": "A missing courier delivers an unsealed message.",
            "narrative_position": 5.0,
            "characters": ["Elena Vareth"],
        }
        side_resp = await client.post(
            "/api/v1/generate/side-story", json=side_payload, headers=headers
        )
        assert side_resp.status_code == 200
        side_data = side_resp.json()
        assert side_data["suggestion_type"] == "side_story"

        # 3. POST /api/v1/generate/continuity-analysis
        cont_payload = {
            "request": "Check if Elena could have spoken to Aldric before the famine winter.",
            "narrative_position": 2.0,
        }
        cont_resp = await client.post(
            "/api/v1/generate/continuity-analysis", json=cont_payload, headers=headers
        )
        assert cont_resp.status_code == 200
        cont_data = cont_resp.json()
        assert cont_data["suggestion_type"] == "continuity_analysis"

        # 4. POST /api/v1/generate/explore-branches (explore branches without a prompt)
        branch_payload = {
            "narrative_position": 5.0,
            "branch_count": 2,
        }
        branch_resp = await client.post(
            "/api/v1/generate/explore-branches", json=branch_payload, headers=headers
        )
        assert branch_resp.status_code == 200
        branch_data = branch_resp.json()
        assert len(branch_data) == 2
        assert branch_data[0]["title"] == "Direct Confrontation at the Toll"
        assert branch_data[1]["title"] == "Covert Night Infiltration"
        assert "validation_results" in branch_data[0]

        # 5. GET /api/v1/suggestions (list all suggestions)
        list_resp = await client.get("/api/v1/suggestions", headers=headers)
        assert list_resp.status_code == 200
        all_sugs = list_resp.json()
        assert len(all_sugs) == 5

        # Filter by type
        filter_resp = await client.get("/api/v1/suggestions?type=plot_point", headers=headers)
        assert filter_resp.status_code == 200
        plot_sugs = filter_resp.json()
        assert len(plot_sugs) == 3
        assert plot_sugs[0]["id"] == suggestion_id

        # 5. GET /api/v1/suggestions/{suggestion_id}
        single_resp = await client.get(f"/api/v1/suggestions/{suggestion_id}", headers=headers)
        assert single_resp.status_code == 200
        single_data = single_resp.json()
        assert single_data["id"] == suggestion_id
        assert single_data["title"] == data["title"]
        assert "validation_results" in single_data
