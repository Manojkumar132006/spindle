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
