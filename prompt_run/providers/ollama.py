"""
providers/ollama.py
-------------------
Ollama provider for running local models.
No API key needed — just run `ollama serve` locally.
Default base URL: http://localhost:11434
Override with OLLAMA_BASE_URL environment variable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import BaseProvider, ProviderResponse, ProviderError

DEFAULT_MODEL = "llama3"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self) -> None:
        self._base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

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

        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
        ).encode("utf-8")

        url = f"{self._base_url}/api/chat"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise ProviderError(
                f"Cannot connect to Ollama at {self._base_url}.\n"
                f"Make sure Ollama is running: `ollama serve`\n"
                f"Error: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise ProviderError(f"Invalid JSON response from Ollama: {e}") from e

        content = data.get("message", {}).get("content", "")
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return ProviderResponse(
            content=content,
            model=model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
