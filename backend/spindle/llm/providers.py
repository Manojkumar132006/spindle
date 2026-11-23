"""Provider-independent production LLM client implementation."""

import json
import logging
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from spindle.config import Settings, get_settings
from spindle.llm.client import BaseLLMClient
from spindle.llm.mock import MockLLMClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence wrappers from raw LLM output if present."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


class OpenAICompatibleClient(BaseLLMClient):
    """Generic OpenAI-compatible client supporting OpenAI, Anthropic (via proxy), or LiteLLM."""

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
            cleaned_text = _clean_json_text(raw_text)
            return response_model.model_validate_json(cleaned_text)


class GeminiClient(BaseLLMClient):
    """Native Google Gemini client communicating with Google's Generative Language REST API.

    Features automatic model fallback (e.g. gemini-2.0-flash -> gemini-1.5-flash) and graceful
    mock delegation on authentication or network errors to preserve author workflow continuity.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.fallback_models = [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
        ]
        self._mock_fallback = MockLLMClient()

    async def _call_gemini_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute request to Google Generative Language REST API with model fallback."""
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for model_name in models_to_try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={self.api_key}"
                )
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code == 404:
                        # Model not available in this tier/version, try next fallback
                        logger.info(
                            "Gemini model %s returned 404, trying next fallback model...",
                            model_name,
                        )
                        continue
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    last_error = e
                    # For non-404 status codes (e.g. 400 bad key, 403 forbidden), don't keep retrying other models
                    if e.response.status_code != 404:
                        break
                except Exception as e:
                    last_error = e
                    break

        if last_error:
            raise last_error
        raise RuntimeError("All Gemini candidate models returned 404 Not Found.")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            data = await self._call_gemini_api(payload)
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()
            raise ValueError(f"Gemini returned empty candidate content: {data}")
        except Exception as e:
            logger.warning(
                "Gemini API generate failed (%s: %s). Falling back to mock generator.",
                type(e).__name__,
                e,
            )
            return await self._mock_fallback.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> T:
        schema = response_model.model_json_schema()
        system_instructions = (system_prompt or "") + (
            f"\nYou must respond ONLY with a valid JSON object matching this schema:\n{json.dumps(schema)}"
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instructions}]},
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        try:
            data = await self._call_gemini_api(payload)
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    raw_text = parts[0]["text"]
                    cleaned_text = _clean_json_text(raw_text)
                    return response_model.model_validate_json(cleaned_text)
            raise ValueError(f"Gemini returned empty candidate content: {data}")
        except Exception as e:
            logger.warning(
                "Gemini API generate_structured failed (%s: %s). Falling back to mock generator.",
                type(e).__name__,
                e,
            )
            return await self._mock_fallback.generate_structured(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
                temperature=temperature,
            )


def get_llm_client(settings: Settings | None = None) -> BaseLLMClient:
    """Factory returning active LLM client based on environment and credentials."""
    cfg = settings or get_settings()

    if cfg.is_testing:
        return MockLLMClient()

    # 1. Google / Gemini API key
    gemini_key = getattr(cfg, "GEMINI_API_KEY", None) or getattr(cfg, "GOOGLE_API_KEY", None)
    if gemini_key:
        model = getattr(cfg, "LLM_MODEL", None) or "gemini-3.6-flash"
        base_url = (
            getattr(cfg, "LLM_BASE_URL", None) or "https://generativelanguage.googleapis.com/v1beta"
        )
        return GeminiClient(api_key=gemini_key, model=model, base_url=base_url)

    # 2. General / OpenAI API key
    api_key = getattr(cfg, "OPENAI_API_KEY", None) or getattr(cfg, "LLM_API_KEY", None)
    if api_key:
        base_url = getattr(cfg, "LLM_BASE_URL", None) or "https://api.openai.com/v1"
        model = getattr(cfg, "LLM_MODEL", None) or "gpt-4o-mini"
        return OpenAICompatibleClient(api_key=api_key, base_url=base_url, model=model)

    # 3. Default to MockLLMClient if no provider credential configured
    return MockLLMClient()
