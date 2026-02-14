"""OpenAI chat-completions API adapter for adaptive profiling."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .base import BaseAPIAdapter

if TYPE_CHECKING:
    from ..types import Item, ModelOutput, RegimeConfig

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"


class OpenAIAdapter(BaseAPIAdapter):
    """Adapter for OpenAI chat-completions API."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = 80,
    ) -> None:
        api_key = api_key or os.environ.get(OPENAI_API_KEY_ENV, "")
        if not api_key:
            raise ValueError(
                f"API key required. Set {OPENAI_API_KEY_ENV} or pass api_key=..."
            )
        super().__init__(model=model, api_key=api_key, max_tokens=max_tokens)
        self._client = None

    @property
    def _openai(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "openai package required. Install with: pip install llmpsycho[openai]"
                ) from e
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def __call__(self, prompt: str, regime: RegimeConfig, item: Item) -> ModelOutput:
        messages = []
        if regime.system_prompt:
            messages.append({"role": "system", "content": regime.system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._openai.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
            temperature=regime.temperature,
        )
        choice = response.choices[0]
        raw_text = choice.message.content or ""
        usage = response.usage
        return self._make_output(
            raw_text=raw_text,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )
