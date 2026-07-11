"""Anthropic Claude client wrapper with structured output support."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from odyssey.config import settings


class LLMClient:
    """Wrapper around Anthropic's Claude API."""

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate a text response from Claude."""
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": model or settings.llm_model,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def generate_structured(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate a JSON-structured response from Claude.

        The prompt should instruct Claude to respond in JSON format.
        """
        full_system = (system + "\n\n" if system else "") + (
            "You MUST respond with valid JSON only. No markdown, no explanation, just JSON."
        )
        text = await self.generate(
            prompt=prompt,
            system=full_system,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)

    async def generate_with_reasoning(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int | None = None,
    ) -> str:
        """Use the reasoning model for complex architecture decisions."""
        return await self.generate(
            prompt=prompt,
            system=system,
            model=settings.llm_reasoning_model,
            max_tokens=max_tokens or 8192,
            temperature=1.0,  # Required for extended thinking models
        )


llm_client = LLMClient()
