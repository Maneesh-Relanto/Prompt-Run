"""
providers/base.py
-----------------
Abstract base class for all LLM providers.
Each provider implements `complete()` and returns a ProviderResponse.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    @property
    def token_summary(self) -> str:
        return f"{self.input_tokens} in / {self.output_tokens} out / {self.total_tokens} total"


class BaseProvider(ABC):
    name: str = ""

    @abstractmethod
    def complete(
        self,
        system: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> ProviderResponse:
        """Send prompt to LLM and return structured response."""
        ...

    def default_model(self) -> str:
        """Return the default model for this provider."""
        return ""

    def stream_complete(
        self,
        system: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        """Stream response tokens one chunk at a time.

        Default implementation fetches the full response and yields it as one
        chunk.  Providers that support native streaming should override this.
        """
        response = self.complete(
            system=system,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield response.content


class ProviderError(Exception):
    pass
