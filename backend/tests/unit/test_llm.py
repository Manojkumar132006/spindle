"""Unit tests for provider-independent LLM client and MockLLM implementation."""

import pytest
from pydantic import BaseModel

from spindle.llm.mock import MockLLMClient


class SampleModel(BaseModel):
    title: str
    score: float


@pytest.mark.asyncio
async def test_mock_llm_text_and_call_history():
    """Test MockLLMClient text generation and execution logging."""
    client = MockLLMClient()
    response = await client.generate(
        "Describe the oath.", system_prompt="You are a narrative engine."
    )

    assert isinstance(response, str)
    assert len(client.call_history) == 1
    assert client.call_history[0]["type"] == "text"
    assert client.call_history[0]["prompt"] == "Describe the oath."


@pytest.mark.asyncio
async def test_mock_llm_structured_enqueued_responses():
    """Test MockLLMClient structured completions and enqueued responses."""
    client = MockLLMClient()
    client.enqueue_response(SampleModel(title="Custom Title", score=9.5))

    structured = await client.generate_structured(
        prompt="Generate sample data",
        response_model=SampleModel,
    )

    assert structured.title == "Custom Title"
    assert structured.score == 9.5
    assert len(client.call_history) == 1
    assert client.call_history[0]["type"] == "structured"
    assert client.call_history[0]["model"] == "SampleModel"


def test_clean_json_text():
    """Verify markdown code block fences are cleanly removed from JSON."""
    from spindle.llm.providers import _clean_json_text

    raw_markdown = '```json\n{"title": "Secret", "score": 8.0}\n```'
    assert _clean_json_text(raw_markdown) == '{"title": "Secret", "score": 8.0}'

    plain_json = '{"title": "Direct"}'
    assert _clean_json_text(plain_json) == '{"title": "Direct"}'


def test_gemini_client_factory():
    """Verify that GEMINI_API_KEY in settings configures GeminiClient."""
    from spindle.config import Settings
    from spindle.llm.providers import GeminiClient, get_llm_client

    gemini_settings = Settings(
        ENVIRONMENT="development",
        GEMINI_API_KEY="AIzaSyDummyGeminiKey123",
        LLM_MODEL="gemini-2.0-flash",
    )
    client = get_llm_client(gemini_settings)
    assert isinstance(client, GeminiClient)
    assert client.api_key == "AIzaSyDummyGeminiKey123"
    assert client.model == "gemini-2.0-flash"
    assert "generativelanguage.googleapis.com" in client.base_url
