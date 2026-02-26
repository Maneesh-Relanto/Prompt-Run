"""
runner.py
---------
Orchestrates the full lifecycle:
  parse .prompt file → render variables → call provider → return response
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .parser import PromptFile, parse_prompt_file, parse_prompt_string
from .renderer import render_prompt, read_stdin_if_piped
from .providers import get_provider, ProviderResponse


@dataclass
class RunConfig:
    """Runtime overrides. Any field set here wins over the .prompt file defaults."""

    vars: dict[str, Any]
    model: str = ""
    provider: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    system: str = ""
    dry_run: bool = False  # print resolved prompt, don't call LLM
    stdin_var: str = ""  # if set, pipe stdin content into this var
    stream: bool = False  # stream tokens to stdout as they arrive


@dataclass
class RunResult:
    prompt_file: PromptFile
    rendered_system: str
    rendered_body: str
    response: ProviderResponse | None  # None in dry-run mode
    dry_run: bool = False


def run_prompt_file(path: Path | str, config: RunConfig) -> RunResult:
    """Parse, render, and execute a .prompt file."""
    pf = parse_prompt_file(path)
    return _run(pf, config)


def run_prompt_string(raw: str, config: RunConfig) -> RunResult:
    """Parse, render, and execute a raw .prompt string (useful for testing)."""
    pf = parse_prompt_string(raw)
    return _run(pf, config)


def stream_run_prompt_file(path: Path | str, config: RunConfig) -> Iterator[str]:
    """Parse, render, and stream tokens from a .prompt file.

    Yields text chunks as they arrive from the provider.
    Callers should set ``config.stream = True`` to signal intent, but this
    function always streams regardless of that flag.
    """
    pf = parse_prompt_file(path)
    yield from _stream(pf, config)


def _resolve_runtime_vars(config: RunConfig, pf: PromptFile) -> dict[str, Any]:
    """Merge config.vars with piped stdin, auto-detecting the target variable."""
    runtime_vars = dict(config.vars)
    piped = read_stdin_if_piped()
    if not piped:
        return runtime_vars
    if config.stdin_var:
        runtime_vars[config.stdin_var] = piped
    else:
        required_vars = [
            name for name, spec in pf.vars.items() if spec.required and name not in runtime_vars
        ]
        if len(required_vars) == 1:
            runtime_vars[required_vars[0]] = piped
    return runtime_vars


def _run(pf: PromptFile, config: RunConfig) -> RunResult:
    """Internal: render + call provider."""
    runtime_vars = _resolve_runtime_vars(config, pf)

    # Render body and system
    rendered_system, rendered_body = render_prompt(pf, runtime_vars)

    # Apply config overrides
    if config.system:
        rendered_system = config.system

    # Dry-run: return without calling LLM
    if config.dry_run:
        return RunResult(
            prompt_file=pf,
            rendered_system=rendered_system,
            rendered_body=rendered_body,
            response=None,
            dry_run=True,
        )

    # Resolve provider and model
    provider_name = config.provider or pf.provider or "anthropic"
    provider = get_provider(provider_name)

    model = config.model or pf.model or provider.default_model()
    temperature = config.temperature if config.temperature is not None else pf.temperature
    max_tokens = config.max_tokens if config.max_tokens is not None else pf.max_tokens

    response = provider.complete(
        system=rendered_system,
        prompt=rendered_body,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return RunResult(
        prompt_file=pf,
        rendered_system=rendered_system,
        rendered_body=rendered_body,
        response=response,
        dry_run=False,
    )


def _stream(pf: PromptFile, config: RunConfig) -> Iterator[str]:
    """Internal: render variables then stream tokens from the provider."""
    runtime_vars = _resolve_runtime_vars(config, pf)
    rendered_system, rendered_body = render_prompt(pf, runtime_vars)
    if config.system:
        rendered_system = config.system

    provider_name = config.provider or pf.provider or "anthropic"
    provider = get_provider(provider_name)

    model = config.model or pf.model or provider.default_model()
    temperature = config.temperature if config.temperature is not None else pf.temperature
    max_tokens = config.max_tokens if config.max_tokens is not None else pf.max_tokens

    yield from provider.stream_complete(
        system=rendered_system,
        prompt=rendered_body,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
