"""Model adapters for real LLM APIs."""

from .anthropic import AnthropicAdapter
from .openai import OpenAIAdapter

__all__ = [
    "AnthropicAdapter",
    "OpenAIAdapter",
]
