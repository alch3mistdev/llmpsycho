"""Base adapter for LLM API integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import Item, ModelOutput, RegimeConfig


class BaseAPIAdapter(ABC):
    """Base class for adapters that call real LLM APIs."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 80,
    ) -> None:
        self.model = model
        self.api_key = api_key or ""
        self.max_tokens = max_tokens

    def _make_output(
        self,
        *,
        raw_text: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> "ModelOutput":
        from ..types import ModelOutput

        return ModelOutput(
            raw_text=raw_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            score_override=None,
        )

    @abstractmethod
    def __call__(self, prompt: str, regime: RegimeConfig, item: Item) -> ModelOutput:
        """Call the model and return ModelOutput."""
        ...
