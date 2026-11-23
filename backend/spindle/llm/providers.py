"""Provider-independent production LLM client implementation."""

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from spindle.config import Settings, get_settings
from spindle.llm.client import BaseLLMClient
from spindle.llm.mock import MockLLMClient

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleClient(BaseLLMClient):
    """Generic OpenAI-compatible client supporting OpenAI, Anthropic (via proxy), Gemini, or LiteLLM."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> T:
        schema = response_model.model_json_schema()
        system_instructions = (system_prompt or "") + (
            f"\nYou must respond ONLY with valid JSON matching this JSON schema:\n{json.dumps(schema)}"
        )

        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": prompt},
        ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            return response_model.model_validate_json(raw_text)


def get_llm_client(settings: Settings | None = None) -> BaseLLMClient:
    """Factory returning active LLM client based on environment and credentials."""
    cfg = settings or get_settings()

    if cfg.is_testing:
        return MockLLMClient()

    # Look for API keys in environment or settings
    api_key = getattr(cfg, "OPENAI_API_KEY", None) or getattr(cfg, "LLM_API_KEY", None)
    if not api_key:
        # Default to MockLLMClient if no provider credential configured
        return MockLLMClient()

    base_url = getattr(cfg, "LLM_BASE_URL", "https://api.openai.com/v1")
    model = getattr(cfg, "LLM_MODEL", "gpt-4o-mini")
    return OpenAICompatibleClient(api_key=api_key, base_url=base_url, model=model)
