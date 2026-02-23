"""Shared pytest fixtures for prompt-run tests."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from prompt_run.providers.base import ProviderResponse


# ── Reusable prompt strings ────────────────────────────────────────────────────

BASIC_PROMPT = """\
---
name: test
provider: anthropic
model: claude-sonnet-4-6
temperature: 0.5
max_tokens: 256
vars:
  text: string
  style: string = bullets
---

Summarize {{text}} as {{style}}.
"""

STATIC_PROMPT = """\
---
name: static
provider: anthropic
---

This prompt has no variables.
"""


@pytest.fixture()
def basic_prompt_str() -> str:
    return BASIC_PROMPT


@pytest.fixture()
def static_prompt_str() -> str:
    return STATIC_PROMPT


@pytest.fixture()
def tmp_prompt_file(tmp_path: Path) -> Path:
    """Write BASIC_PROMPT to a temp .prompt file and return the path."""
    p = tmp_path / "test.prompt"
    p.write_text(BASIC_PROMPT, encoding="utf-8")
    return p


@pytest.fixture()
def mock_provider_response() -> ProviderResponse:
    return ProviderResponse(
        content="• Point one\n• Point two",
        model="claude-sonnet-4-6",
        provider="anthropic",
        input_tokens=50,
        output_tokens=20,
        total_tokens=70,
    )


@pytest.fixture()
def mock_anthropic_provider(mock_provider_response: ProviderResponse) -> MagicMock:
    """A MagicMock that quacks like AnthropicProvider."""
    provider = MagicMock()
    provider.complete.return_value = mock_provider_response
    provider.stream_complete.return_value = iter(["• Point one\n• Point two"])
    provider.default_model.return_value = "claude-sonnet-4-6"
    return provider
