"""
diff.py
-------
Runs a prompt with two different inputs (or two prompt files with same input)
and shows outputs side by side.

Two modes:
  1. Same prompt file, different --a-var / --b-var sets
  2. Two different .prompt files, same --var set
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runner import run_prompt_file, RunConfig, RunResult


@dataclass
class DiffResult:
    label_a: str
    label_b: str
    result_a: RunResult
    result_b: RunResult


def run_diff(
    prompt_a: Path,
    prompt_b: Path,
    vars_a: dict[str, Any],
    vars_b: dict[str, Any],
    config: RunConfig,
    label_a: str = "A",
    label_b: str = "B",
) -> DiffResult:
    """
    Run two prompts (may be same file) with two var sets.
    Returns both results for display.
    """
    config_a = RunConfig(
        vars=vars_a,
        model=config.model,
        provider=config.provider,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        system=config.system,
        dry_run=config.dry_run,
    )
    config_b = RunConfig(
        vars=vars_b,
        model=config.model,
        provider=config.provider,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        system=config.system,
        dry_run=config.dry_run,
    )

    result_a = run_prompt_file(prompt_a, config_a)
    result_b = run_prompt_file(prompt_b, config_b)

    return DiffResult(
        label_a=label_a,
        label_b=label_b,
        result_a=result_a,
        result_b=result_b,
    )


def format_diff_plain(diff: DiffResult, width: int = 100) -> str:
    """
    Format diff results as a side-by-side plain-text table.
    Falls back to stacked view if terminal is narrow.
    """
    col_w = (width - 7) // 2  # 7 = borders + padding

    def _wrap(text: str) -> list[str]:
        lines = []
        for paragraph in text.splitlines():
            if paragraph.strip():
                lines.extend(textwrap.wrap(paragraph, col_w) or [""])
            else:
                lines.append("")
        return lines or ["(empty)"]

    content_a = diff.result_a.response.content if diff.result_a.response else diff.result_a.rendered_body
    content_b = diff.result_b.response.content if diff.result_b.response else diff.result_b.rendered_body

    lines_a = _wrap(content_a)
    lines_b = _wrap(content_b)

    max_lines = max(len(lines_a), len(lines_b))
    lines_a += [""] * (max_lines - len(lines_a))
    lines_b += [""] * (max_lines - len(lines_b))

    separator = "─" * col_w
    header = f"┌─ {diff.label_a:<{col_w - 3}}┬─ {diff.label_b:<{col_w - 3}}┐"
    div = f"├{'─' * (col_w + 1)}┼{'─' * (col_w + 1)}┤"
    footer = f"└{'─' * (col_w + 1)}┴{'─' * (col_w + 1)}┘"

    rows = [header]
    for la, lb in zip(lines_a, lines_b):
        rows.append(f"│ {la:<{col_w - 1}}│ {lb:<{col_w - 1}}│")
    rows.append(footer)

    # Token stats footer
    if diff.result_a.response and diff.result_b.response:
        rows.append("")
        rows.append(
            f"  Tokens — {diff.label_a}: {diff.result_a.response.token_summary} "
            f"| {diff.label_b}: {diff.result_b.response.token_summary}"
        )

    return "\n".join(rows)
