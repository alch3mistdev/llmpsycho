"""Anthropic Claude API adapter for adaptive profiling."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .base import BaseAPIAdapter

if TYPE_CHECKING:
    from ..types import Item, ModelOutput, RegimeConfig

ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"


class AnthropicAdapter(BaseAPIAdapter):
    """Adapter for Anthropic Claude chat-completions API."""

    def __init__(
        self,
        *,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        max_tokens: int = 80,
    ) -> None:
        api_key = api_key or os.environ.get(ANTHROPIC_API_KEY_ENV, "")
        if not api_key:
            raise ValueError(
                f"API key required. Set {ANTHROPIC_API_KEY_ENV} or pass api_key=..."
            )
        super().__init__(model=model, api_key=api_key, max_tokens=max_tokens)
        self._client = None

    @property
    def _anthropic(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise ImportError(
                    "anthropic package required. Install with: pip install llmpsycho[anthropic]"
                ) from e
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def __call__(self, prompt: str, regime: RegimeConfig, item: Item) -> ModelOutput:
        response = self._anthropic.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=regime.system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=regime.temperature,
        )
        raw_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw_text += block.text
        return self._make_output(
            raw_text=raw_text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )
