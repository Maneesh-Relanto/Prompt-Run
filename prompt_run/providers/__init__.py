"""
providers/__init__.py
---------------------
Provider registry and factory function.
"""

from __future__ import annotations

from .base import BaseProvider, ProviderResponse, ProviderError
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .ollama import OllamaProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def get_provider(name: str) -> BaseProvider:
    """Instantiate and return a provider by name."""
    name = name.lower().strip()
    if name not in PROVIDERS:
        raise ProviderError(
            f"Unknown provider '{name}'. "
            f"Available: {', '.join(sorted(PROVIDERS.keys()))}"
        )
    return PROVIDERS[name]()


__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "ProviderError",
    "get_provider",
    "PROVIDERS",
]
