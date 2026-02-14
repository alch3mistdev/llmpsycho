"""Adaptive psychometric profiler package."""

from .config import RunConfig
from .engine import AdaptiveProfilerEngine
from .item_bank import build_item_bank
from .simulate import SimulatedModelAdapter

__all__ = [
    "AdaptiveProfilerEngine",
    "RunConfig",
    "SimulatedModelAdapter",
    "build_item_bank",
]

# API adapters for Anthropic and OpenAI (require pip install llmpsycho[anthropic] or llmpsycho[openai])
from .adapters import AnthropicAdapter, OpenAIAdapter

__all__ += ["AnthropicAdapter", "OpenAIAdapter"]
