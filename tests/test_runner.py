"""
Tests for prompt_run.runner — orchestration layer.
Provider calls are mocked; no real API keys needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from prompt_run.runner import (
    RunConfig,
    RunResult,
    run_prompt_file,
    run_prompt_string,
    stream_run_prompt_file,
    _resolve_runtime_vars,
)
from prompt_run.parser import parse_prompt_string
from prompt_run.providers.base import ProviderResponse, ProviderError


# Silence stdin reads in all tests by default
@pytest.fixture(autouse=True)
def _no_stdin(monkeypatch):
    monkeypatch.setattr("prompt_run.runner.read_stdin_if_piped", lambda: None)


# ── Fixtures ───────────────────────────────────────────────────────────────────

SIMPLE_RAW = """\
---
provider: anthropic
model: claude-sonnet-4-6
vars:
  text: string
---

Summarize {{text}}.
"""

_MOCK_RESPONSE = ProviderResponse(
    content="• Bullet one",
    model="claude-sonnet-4-6",
    provider="anthropic",
    input_tokens=20,
    output_tokens=10,
    total_tokens=30,
)


def _mock_provider(response: ProviderResponse = _MOCK_RESPONSE) -> MagicMock:
    p = MagicMock()
    p.complete.return_value = response
    p.stream_complete.return_value = iter(["chunk1", " chunk2"])
    p.default_model.return_value = "claude-sonnet-4-6"
    return p


def _config(**kwargs) -> RunConfig:
    defaults: dict[str, Any] = {"vars": {}, "model": "", "provider": "", "temperature": None, "max_tokens": None, "system": "", "dry_run": False}
    defaults.update(kwargs)
    return RunConfig(**defaults)


# ── run_prompt_string ──────────────────────────────────────────────────────────

class TestRunPromptString:
    def test_returns_run_result(self):
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            result = run_prompt_string(SIMPLE_RAW, _config(vars={"text": "hello"}))
        assert isinstance(result, RunResult)
        assert result.response is not None
        assert result.response.content == "• Bullet one"

    def test_dry_run_returns_no_response(self):
        result = run_prompt_string(SIMPLE_RAW, _config(vars={"text": "hello"}, dry_run=True))
        assert result.dry_run is True
        assert result.response is None
        assert "hello" in result.rendered_body


# ── run_prompt_file ────────────────────────────────────────────────────────────

class TestRunPromptFile:
    def test_run_from_file(self, tmp_path: Path):
        p = tmp_path / "test.prompt"
        p.write_text(SIMPLE_RAW, encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            result = run_prompt_file(p, _config(vars={"text": "world"}))
        assert result.response.content == "• Bullet one"

    def test_system_override_replaces_file_system(self, tmp_path: Path):
        raw = "---\nsystem: Original system.\nprovider: anthropic\n---\nHello"
        p = tmp_path / "test.prompt"
        p.write_text(raw, encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            result = run_prompt_file(p, _config(system="Override system."))
        assert result.rendered_system == "Override system."

    def test_model_override(self, tmp_path: Path):
        p = tmp_path / "test.prompt"
        p.write_text("---\nprovider: anthropic\nmodel: claude-sonnet-4-6\n---\nHello", encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            run_prompt_file(p, _config(model="gpt-4o", provider="openai"))
        call_kwargs = mock_prov.complete.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_temperature_override(self, tmp_path: Path):
        p = tmp_path / "test.prompt"
        p.write_text("---\nprovider: anthropic\ntemperature: 0.3\n---\nHello", encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            run_prompt_file(p, _config(temperature=0.9))
        call_kwargs = mock_prov.complete.call_args[1]
        assert call_kwargs["temperature"] == pytest.approx(0.9)

    def test_max_tokens_override(self, tmp_path: Path):
        p = tmp_path / "test.prompt"
        p.write_text("---\nprovider: anthropic\nmax_tokens: 256\n---\nHello", encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            run_prompt_file(p, _config(max_tokens=2048))
        call_kwargs = mock_prov.complete.call_args[1]
        assert call_kwargs["max_tokens"] == 2048

    def test_uses_file_temperature_when_no_override(self, tmp_path: Path):
        p = tmp_path / "test.prompt"
        p.write_text("---\nprovider: anthropic\ntemperature: 0.1\n---\nHello", encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            run_prompt_file(p, _config())  # no temperature override
        call_kwargs = mock_prov.complete.call_args[1]
        assert call_kwargs["temperature"] == pytest.approx(0.1)


# ── stream_run_prompt_file ─────────────────────────────────────────────────────

class TestStreamRunPromptFile:
    def test_yields_chunks(self, tmp_path: Path):
        p = tmp_path / "test.prompt"
        p.write_text(SIMPLE_RAW, encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            chunks = list(stream_run_prompt_file(p, _config(vars={"text": "hello"})))
        assert chunks == ["chunk1", " chunk2"]
        mock_prov.stream_complete.assert_called_once()

    def test_stream_with_system_override(self, tmp_path: Path):
        raw = "---\nprovider: anthropic\nvars:\n  text: string\n---\n{{text}}"
        p = tmp_path / "test.prompt"
        p.write_text(raw, encoding="utf-8")
        mock_prov = _mock_provider()
        with patch("prompt_run.runner.get_provider", return_value=mock_prov):
            list(stream_run_prompt_file(p, _config(vars={"text": "hi"}, system="Override")))
        call_kwargs = mock_prov.stream_complete.call_args[1]
        assert call_kwargs["system"] == "Override"


# ── _resolve_runtime_vars (stdin injection) ────────────────────────────────────

class TestResolveRuntimeVars:
    def test_no_stdin_returns_config_vars(self, monkeypatch):
        monkeypatch.setattr("prompt_run.runner.read_stdin_if_piped", lambda: None)
        pf = parse_prompt_string(SIMPLE_RAW)
        config = _config(vars={"text": "hello"})
        resolved = _resolve_runtime_vars(config, pf)
        assert resolved == {"text": "hello"}

    def test_explicit_stdin_var_injects_into_named_var(self, monkeypatch):
        monkeypatch.setattr("prompt_run.runner.read_stdin_if_piped", lambda: "piped content")
        pf = parse_prompt_string(SIMPLE_RAW)
        config = _config(vars={}, stdin_var="text")
        resolved = _resolve_runtime_vars(config, pf)
        assert resolved["text"] == "piped content"

    def test_auto_detect_single_required_var(self, monkeypatch):
        monkeypatch.setattr("prompt_run.runner.read_stdin_if_piped", lambda: "auto content")
        pf = parse_prompt_string(SIMPLE_RAW)
        config = _config(vars={})
        resolved = _resolve_runtime_vars(config, pf)
        assert resolved["text"] == "auto content"

    def test_no_auto_detect_when_multiple_required_vars(self, monkeypatch):
        monkeypatch.setattr("prompt_run.runner.read_stdin_if_piped", lambda: "piped")
        raw = "---\nvars:\n  a: string\n  b: string\n---\n{{a}} {{b}}"
        pf = parse_prompt_string(raw)
        config = _config(vars={})
        resolved = _resolve_runtime_vars(config, pf)
        assert "a" not in resolved
        assert "b" not in resolved

    def test_no_auto_detect_when_var_already_provided(self, monkeypatch):
        monkeypatch.setattr("prompt_run.runner.read_stdin_if_piped", lambda: "piped")
        pf = parse_prompt_string(SIMPLE_RAW)
        config = _config(vars={"text": "already set"})
        resolved = _resolve_runtime_vars(config, pf)
        assert resolved["text"] == "already set"
