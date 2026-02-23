"""
providers/openai.py
-------------------
OpenAI provider using the official openai SDK.
Auth: OPENAI_API_KEY environment variable.
Also supports Azure OpenAI via OPENAI_API_BASE + OPENAI_API_VERSION.
"""

from __future__ import annotations

import os
from typing import Iterator

from .base import BaseProvider, ProviderResponse, ProviderError

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self):
        try:
            import openai as openai_sdk
            self._sdk = openai_sdk
        except ImportError:
            raise ProviderError(
                "The `openai` package is not installed.\n"
                "Run: pip install openai"
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError(
                "OPENAI_API_KEY environment variable is not set.\n"
                "Get your key at https://platform.openai.com/api-keys"
            )

        # Optional Azure support
        base_url = os.environ.get("OPENAI_API_BASE")
        api_version = os.environ.get("OPENAI_API_VERSION")

        if base_url and api_version:
            self._client = self._sdk.AzureOpenAI(
                api_key=api_key,
                azure_endpoint=base_url,
                api_version=api_version,
            )
        else:
            self._client = self._sdk.OpenAI(api_key=api_key)

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

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except self._sdk.AuthenticationError:
            raise ProviderError(
                "Authentication failed. Check your OPENAI_API_KEY."
            )
        except self._sdk.RateLimitError:
            raise ProviderError("Rate limit hit. Please wait and try again.")
        except self._sdk.APIConnectionError as e:
            raise ProviderError(f"Connection error: {e}") from e
        except self._sdk.APIStatusError as e:
            raise ProviderError(f"API error {e.status_code}: {e.message}") from e

        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage

        return ProviderResponse(
            content=content,
            model=response.model,
            provider=self.name,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
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

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except self._sdk.AuthenticationError:
            raise ProviderError("Authentication failed. Check your OPENAI_API_KEY.")
        except self._sdk.RateLimitError:
            raise ProviderError("Rate limit hit. Please wait and try again.")
        except self._sdk.APIConnectionError as e:
            raise ProviderError(f"Connection error: {e}") from e
        except self._sdk.APIStatusError as e:
            raise ProviderError(f"API error {e.status_code}: {e.message}") from e
