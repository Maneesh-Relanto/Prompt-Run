"""
providers/anthropic.py
----------------------
Anthropic Claude provider using the official anthropic SDK.
Auth: ANTHROPIC_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Iterator

from .base import BaseProvider, ProviderResponse, ProviderError

DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self):
        try:
            import anthropic as anthropic_sdk
            self._sdk = anthropic_sdk
        except ImportError:
            raise ProviderError(
                "The `anthropic` package is not installed.\n"
                "Run: pip install anthropic"
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not set.\n"
                "\n"
                "  Fix it:\n"
                "    export ANTHROPIC_API_KEY='sk-ant-...'\n"
                "\n"
                "  Get a key at: https://console.anthropic.com/settings/keys"
            )
        self._client = self._sdk.Anthropic(api_key=api_key)

    def default_model(self) -> str:
        return DEFAULT_MODEL

    def complete(
        self,
        system: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> ProviderResponse:
        model = model or DEFAULT_MODEL

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        try:
            response = self._client.messages.create(**kwargs)
        except self._sdk.APIConnectionError as e:
            raise ProviderError(f"Connection error: {e}") from e
        except self._sdk.AuthenticationError:
            raise ProviderError(
                "Anthropic authentication failed.\n"
                "\n"
                "  Your ANTHROPIC_API_KEY may be invalid or revoked.\n"
                "  Check it at: https://console.anthropic.com/settings/keys"
            )
        except self._sdk.RateLimitError:
            raise ProviderError("Rate limit hit. Please wait and try again.")
        except self._sdk.APIStatusError as e:
            raise ProviderError(f"API error {e.status_code}: {e.message}") from e

        content = response.content[0].text if response.content else ""
        usage = response.usage

        return ProviderResponse(
            content=content,
            model=response.model,
            provider=self.name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
        )

    def stream_complete(
        self,
        system: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        model = model or DEFAULT_MODEL

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except self._sdk.APIConnectionError as e:
            raise ProviderError(f"Connection error: {e}") from e
        except self._sdk.AuthenticationError:
            raise ProviderError(
                "Anthropic authentication failed.\n"
                "\n"
                "  Your ANTHROPIC_API_KEY may be invalid or revoked.\n"
                "  Check it at: https://console.anthropic.com/settings/keys"
            )
        except self._sdk.RateLimitError:
            raise ProviderError(
                "Anthropic rate limit exceeded.\n"
                "  Wait a moment and try again, or check your usage at\n"
                "  https://console.anthropic.com/settings/limits"
            )
        except self._sdk.APIStatusError as e:
            raise ProviderError(f"API error {e.status_code}: {e.message}") from e
