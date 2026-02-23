"""Tests for the CLI commands in prompt_run.cli."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from prompt_run.cli import cli
from prompt_run.providers.base import ProviderResponse


# ── Helpers ────────────────────────────────────────────────────────────────────

RUNNER = CliRunner()

_MOCK_RESPONSE = ProviderResponse(
    content="• Point one\n• Point two",
    model="claude-sonnet-4-6",
    provider="anthropic",
    input_tokens=50,
    output_tokens=20,
    total_tokens=70,
)


def _make_prompt(tmp_path: Path, body: str = "Summarize {{text}}.") -> Path:
    p = tmp_path / "test.prompt"
    p.write_text(
        f"---\nprovider: anthropic\nmodel: claude-sonnet-4-6\nvars:\n  text: string\n---\n\n{body}",
        encoding="utf-8",
    )
    return p


# ── prompt run ─────────────────────────────────────────────────────────────────

class TestCmdRun:
    def test_dry_run_prints_resolved_prompt(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        result = RUNNER.invoke(cli, ["run", str(p), "--var", "text=hello", "--dry-run"])
        assert result.exit_code == 0
        assert "hello" in result.output
        assert "Dry run" in result.output

    def test_missing_required_var_exits_1(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        result = RUNNER.invoke(cli, ["run", str(p)])
        assert result.exit_code == 1
        assert "text" in result.output  # error mentions missing var

    def test_run_plain_output(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        with patch("prompt_run.cli.run_prompt_file") as mock_run:
            from prompt_run.runner import RunResult
            from prompt_run.parser import parse_prompt_string
            pf = parse_prompt_string("---\nprovider: anthropic\n---\nHello")
            mock_run.return_value = RunResult(
                prompt_file=pf,
                rendered_system="",
                rendered_body="Summarize hello.",
                response=_MOCK_RESPONSE,
                dry_run=False,
            )
            result = RUNNER.invoke(cli, ["run", str(p), "--var", "text=hello"])
        assert result.exit_code == 0
        assert "Point one" in result.output

    def test_run_json_output(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        with patch("prompt_run.cli.run_prompt_file") as mock_run:
            from prompt_run.runner import RunResult
            from prompt_run.parser import parse_prompt_string
            pf = parse_prompt_string("---\nprovider: anthropic\n---\nHello")
            mock_run.return_value = RunResult(
                prompt_file=pf,
                rendered_system="",
                rendered_body="Summarize hello.",
                response=_MOCK_RESPONSE,
                dry_run=False,
            )
            result = RUNNER.invoke(cli, ["run", str(p), "--var", "text=hello", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["response"] == "• Point one\n• Point two"
        assert data["tokens"]["input"] == 50

    def test_stream_flag_calls_stream_runner(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        with patch("prompt_run.cli.stream_run_prompt_file") as mock_stream:
            mock_stream.return_value = iter(["chunk1", "chunk2"])
            result = RUNNER.invoke(cli, ["run", str(p), "--var", "text=hello", "--stream"])
        assert result.exit_code == 0
        assert "chunk1" in result.output
        assert "chunk2" in result.output
        mock_stream.assert_called_once()


# ── prompt validate ────────────────────────────────────────────────────────────

class TestCmdValidate:
    def test_valid_file_exits_0(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        result = RUNNER.invoke(cli, ["validate", str(p)])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_invalid_provider_exits_1(self, tmp_path: Path):
        p = tmp_path / "bad.prompt"
        p.write_text("---\nprovider: imaginary-provider\n---\nHello", encoding="utf-8")
        result = RUNNER.invoke(cli, ["validate", str(p)])
        assert result.exit_code == 1
        assert "INVALID" in result.output

    def test_empty_body_exits_1(self, tmp_path: Path):
        p = tmp_path / "empty.prompt"
        p.write_text("---\nprovider: anthropic\n---\n   ", encoding="utf-8")
        result = RUNNER.invoke(cli, ["validate", str(p)])
        assert result.exit_code == 1

    def test_no_files_exits_1(self):
        result = RUNNER.invoke(cli, ["validate"])
        assert result.exit_code == 1

    def test_multiple_files_all_valid(self, tmp_path: Path):
        p1 = _make_prompt(tmp_path)
        p2 = tmp_path / "static.prompt"
        p2.write_text("---\nprovider: anthropic\n---\nHello world.", encoding="utf-8")
        result = RUNNER.invoke(cli, ["validate", str(p1), str(p2)])
        assert result.exit_code == 0


# ── prompt inspect ─────────────────────────────────────────────────────────────

class TestCmdInspect:
    def test_inspect_shows_metadata(self, tmp_path: Path):
        p = tmp_path / "named.prompt"
        p.write_text(
            "---\nname: my-prompt\nprovider: openai\nmodel: gpt-4o\n---\nHello",
            encoding="utf-8",
        )
        result = RUNNER.invoke(cli, ["inspect", str(p)])
        assert result.exit_code == 0
        assert "my-prompt" in result.output
        assert "openai" in result.output
        assert "gpt-4o" in result.output

    def test_inspect_renders_with_vars(self, tmp_path: Path):
        p = _make_prompt(tmp_path, body="Summarize {{text}}.")
        result = RUNNER.invoke(cli, ["inspect", str(p), "--var", "text=hello world"])
        assert result.exit_code == 0
        assert "hello world" in result.output


# ── prompt diff ────────────────────────────────────────────────────────────────

class TestCmdDiff:
    def test_diff_dry_run(self, tmp_path: Path):
        p = _make_prompt(tmp_path)
        result = RUNNER.invoke(
            cli,
            ["diff", str(p), "--a-var", "text=first", "--b-var", "text=second", "--dry-run"],
        )
        # Dry-run diff renders prompts without calling LLM
        assert result.exit_code == 0
