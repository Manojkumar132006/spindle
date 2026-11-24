"""Unit tests for provider-independent LLM client and Gemini/OpenAI implementations."""

import pytest
from pydantic import BaseModel

from spindle.config import Settings
from spindle.llm.providers import (
    GeminiClient,
    OpenAICompatibleClient,
    _clean_json_text,
    get_llm_client,
)


class SampleModel(BaseModel):
    title: str
    score: float


def test_clean_json_text():
    """Verify markdown code block fences are cleanly removed from JSON."""
    raw_markdown = '```json\n{"title": "Secret", "score": 8.0}\n```'
    assert _clean_json_text(raw_markdown) == '{"title": "Secret", "score": 8.0}'

    plain_json = '{"title": "Direct"}'
    assert _clean_json_text(plain_json) == '{"title": "Direct"}'


def test_gemini_client_factory():
    """Verify that GEMINI_API_KEY in settings configures GeminiClient."""
    gemini_settings = Settings(
        ENVIRONMENT="development",
        GEMINI_API_KEY="AIzaSyDummyGeminiKey123",
        LLM_MODEL="gemini-3.6-flash",
    )
    client = get_llm_client(gemini_settings)
    assert isinstance(client, GeminiClient)
    assert client.api_key == "AIzaSyDummyGeminiKey123"
    assert client.model == "gemini-3.6-flash"
    assert "generativelanguage.googleapis.com" in client.base_url
    assert "gemini-3.6-flash" in client.fallback_models


def test_openai_client_factory():
    """Verify that OPENAI_API_KEY in settings configures OpenAICompatibleClient."""
    openai_settings = Settings(
        ENVIRONMENT="development",
        GEMINI_API_KEY=None,
        GOOGLE_API_KEY=None,
        OPENAI_API_KEY="sk-dummy-openai-key",
        LLM_MODEL="gpt-4o",
    )
    client = get_llm_client(openai_settings)
    assert isinstance(client, OpenAICompatibleClient)
    assert client.api_key == "sk-dummy-openai-key"
    assert client.model == "gpt-4o"
    assert client.base_url == "https://api.openai.com/v1"


def test_get_llm_client_raises_when_no_credentials():
    """Verify that get_llm_client raises RuntimeError when no provider credentials exist."""
    empty_settings = Settings(
        ENVIRONMENT="development",
        GEMINI_API_KEY=None,
        GOOGLE_API_KEY=None,
        OPENAI_API_KEY=None,
        LLM_API_KEY=None,
    )
    with pytest.raises(RuntimeError, match="No LLM API key configured"):
        get_llm_client(empty_settings)
