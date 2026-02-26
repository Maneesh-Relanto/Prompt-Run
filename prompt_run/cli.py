"""
cli.py
------
Command-line interface for prompt-run.

Commands:
  prompt run       — run a .prompt file against an LLM
  prompt diff      — compare two prompt outputs side by side
  prompt validate  — static check a .prompt file
  prompt inspect   — show resolved prompt without calling LLM
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import click

from prompt_run.parser import parse_prompt_file, validate_prompt_file, PromptParseError
from prompt_run.renderer import render_prompt, PromptRenderError
from prompt_run.runner import run_prompt_file, stream_run_prompt_file, RunConfig, RunResult
from prompt_run.diff import run_diff, format_diff_plain
from prompt_run.providers import ProviderError


# ── Shared helpers ──────────────────────────────────────────────────────────────


def _parse_vars(var_list: tuple[str, ...]) -> dict[str, Any]:
    """Parse KEY=VALUE pairs from --var flags."""
    result = {}
    for item in var_list:
        if "=" not in item:
            raise click.BadParameter(
                f"Variable must be in KEY=VALUE format, got: '{item}'",
                param_hint="--var",
            )
        key, _, value = item.partition("=")
        result[key.strip()] = value
    return result


def _echo_error(msg: str) -> None:
    click.echo(click.style(f"\n❌ {msg}", fg="red"), err=True)


def _echo_warning(msg: str) -> None:
    click.echo(click.style(f"⚠️  {msg}", fg="yellow"), err=True)


def _echo_success(msg: str) -> None:
    click.echo(click.style(msg, fg="green"))


# ── CLI root ────────────────────────────────────────────────────────────────────


@click.group()
@click.version_option(package_name="prompt-run")
def cli() -> None:
    """
    \b
    prompt-run — treat prompts as first-class files.

    Run, diff, validate, and inspect .prompt files
    against any LLM provider from the command line.

    \b
    Quick start:
      prompt run summarize.prompt --var text="Hello world"
      prompt diff a.prompt b.prompt --var text="test input"
      prompt validate translate.prompt
      prompt inspect summarize.prompt --var text="Hi"
    """


# ── prompt run helpers ─────────────────────────────────────────────────────────


def _stream_run(
    prompt_file: Path,
    config: RunConfig,
    show_prompt: bool,
    runtime_vars: dict[str, Any],
) -> None:
    """Execute streaming run, printing chunks to stdout."""
    if show_prompt:
        from prompt_run.parser import parse_prompt_file as _pf
        from prompt_run.renderer import render_prompt as _rp

        _parsed = _pf(prompt_file)
        _, _body = _rp(_parsed, runtime_vars)
        click.echo(click.style("── Resolved prompt ──", fg="cyan"))
        click.echo(_body)
        click.echo(click.style("── Response ──", fg="cyan"))
    try:
        for chunk in stream_run_prompt_file(prompt_file, config):
            click.echo(chunk, nl=False)
        click.echo()
    except (PromptParseError, PromptRenderError, ProviderError) as e:
        _echo_error(str(e))
        sys.exit(1)


def _print_dry_run(result: RunResult) -> None:
    """Print resolved prompt for dry-run mode."""
    click.echo(click.style("── Dry run — resolved prompt ──", fg="cyan", bold=True))
    if result.rendered_system:
        click.echo(click.style("[system]", fg="blue"))
        click.echo(result.rendered_system)
        click.echo()
    click.echo(click.style("[user]", fg="blue"))
    click.echo(result.rendered_body)


def _write_plain_response(result: RunResult, output_file: str) -> None:
    """Write or print the plain-text response with token summary to stderr."""
    if not result.response:
        return
    content = result.response.content
    if output_file:
        Path(output_file).write_text(content, encoding="utf-8")
        _echo_success(f"\u2705 Response saved to {output_file}")
    else:
        click.echo(content)
    click.echo(
        click.style(
            f"\n[{result.response.provider}/{result.response.model} \u00b7 "
            f"{result.response.token_summary}]",
            fg="bright_black",
        ),
        err=True,
    )


def _print_run_result(
    result: RunResult,
    output_json: bool,
    show_prompt: bool,
    output_file: str,
) -> None:
    """Print the run result as JSON or plain text."""
    if show_prompt:
        click.echo(click.style("── Resolved prompt ──", fg="cyan"))
        click.echo(result.rendered_body)
        click.echo(click.style("── Response ──", fg="cyan"))

    if output_json:
        out = {
            "prompt": result.rendered_body,
            "system": result.rendered_system,
            "response": result.response.content if result.response else "",
            "model": result.response.model if result.response else "",
            "provider": result.response.provider if result.response else "",
            "tokens": {
                "input": result.response.input_tokens if result.response else 0,
                "output": result.response.output_tokens if result.response else 0,
                "total": result.response.total_tokens if result.response else 0,
            },
        }
        click.echo(json.dumps(out, indent=2))
        return

    _write_plain_response(result, output_file)


# ── prompt run ──────────────────────────────────────────────────────────────────


@cli.command("run")
@click.argument("prompt_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--var",
    "vars_list",
    multiple=True,
    metavar="KEY=VALUE",
    help="Variable to inject. Repeatable. e.g. --var text='hello'",
)
@click.option("--model", default="", help="Override model from file")
@click.option("--provider", default="", help="Override provider (anthropic|openai|ollama)")
@click.option("--temperature", type=float, default=None, help="Override temperature (0.0–2.0)")
@click.option("--max-tokens", type=int, default=None, help="Override max output tokens")
@click.option("--system", default="", help="Override or set system prompt")
@click.option("--dry-run", is_flag=True, help="Print resolved prompt without calling LLM")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON with metadata")
@click.option("--show-prompt", is_flag=True, help="Print the rendered prompt before the response")
@click.option("--stream", "use_stream", is_flag=True, help="Stream tokens to stdout as they arrive")
@click.option(
    "--stdin-var",
    default="",
    metavar="VAR",
    help="Pipe stdin into this variable name instead of auto-detecting",
)
@click.option(
    "--output",
    "output_file",
    default="",
    metavar="FILE",
    help="Write response to FILE instead of stdout",
)
def cmd_run(
    prompt_file: Path,
    vars_list: tuple[str, ...],
    model: str,
    provider: str,
    temperature: float | None,
    max_tokens: int | None,
    system: str,
    dry_run: bool,
    output_json: bool,
    show_prompt: bool,
    use_stream: bool,
    stdin_var: str,
    output_file: str,
) -> None:
    """Run a .prompt file against an LLM provider.

    \b
    Examples:
      prompt run summarize.prompt --var text="Hello world"
      prompt run translate.prompt --var text="Bonjour" --var lang=English
      prompt run summarize.prompt --model gpt-4o --provider openai
      prompt run summarize.prompt --dry-run
      cat article.txt | prompt run summarize.prompt
    """
    try:
        runtime_vars = _parse_vars(vars_list)

        config = RunConfig(
            vars=runtime_vars,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
            dry_run=dry_run,
            stdin_var=stdin_var,
            stream=use_stream,
        )

        if use_stream and not dry_run and not output_json:
            _stream_run(prompt_file, config, show_prompt, runtime_vars)
            return

        result = run_prompt_file(prompt_file, config)

    except PromptParseError as e:
        _echo_error(f"Parse error in {prompt_file}:\n{e}")
        sys.exit(1)
    except PromptRenderError as e:
        _echo_error(f"Variable error:\n{e}")
        sys.exit(1)
    except ProviderError as e:
        _echo_error(f"Provider error:\n{e}")
        sys.exit(1)

    if dry_run:
        _print_dry_run(result)
        return

    _print_run_result(result, output_json, show_prompt, output_file)


# ── prompt diff ─────────────────────────────────────────────────────────────────


@cli.command("diff")
@click.argument("prompt_a", type=click.Path(exists=True, path_type=Path))
@click.argument("prompt_b", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--var", "vars_list", multiple=True, metavar="KEY=VALUE", help="Shared variable for both sides"
)
@click.option(
    "--a-var", "a_vars_list", multiple=True, metavar="KEY=VALUE", help="Variable for side A only"
)
@click.option(
    "--b-var", "b_vars_list", multiple=True, metavar="KEY=VALUE", help="Variable for side B only"
)
@click.option("--model", default="", help="Override model")
@click.option("--provider", default="", help="Override provider")
@click.option("--temperature", type=float, default=None)
@click.option("--max-tokens", type=int, default=None)
@click.option("--dry-run", is_flag=True, help="Diff resolved prompts without calling LLM")
@click.option("--json", "output_json", is_flag=True)
def cmd_diff(
    prompt_a: Path,
    prompt_b: Path | None,
    vars_list: tuple[str, ...],
    a_vars_list: tuple[str, ...],
    b_vars_list: tuple[str, ...],
    model: str,
    provider: str,
    temperature: float | None,
    max_tokens: int | None,
    dry_run: bool,
    output_json: bool,
) -> None:
    """Compare two prompt outputs side by side.

    \b
    Mode 1 — same file, different inputs:
      prompt diff summarize.prompt \\
        --a-var text="Article one..." \\
        --b-var text="Article two..."

    \b
    Mode 2 — two prompt versions, same input:
      prompt diff v1.prompt v2.prompt --var text="Same input"
    """
    # If only one file given, use it for both sides
    if prompt_b is None:
        prompt_b = prompt_a

    shared_vars = _parse_vars(vars_list)
    vars_a = {**shared_vars, **_parse_vars(a_vars_list)}
    vars_b = {**shared_vars, **_parse_vars(b_vars_list)}

    label_a = prompt_a.name if prompt_b != prompt_a else "Input A"
    label_b = prompt_b.name if prompt_b != prompt_a else "Input B"

    config = RunConfig(
        vars={},
        model=model,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        dry_run=dry_run,
    )

    try:
        diff = run_diff(
            prompt_a=prompt_a,
            prompt_b=prompt_b,
            vars_a=vars_a,
            vars_b=vars_b,
            config=config,
            label_a=label_a,
            label_b=label_b,
        )
    except (PromptParseError, PromptRenderError, ProviderError) as e:
        _echo_error(str(e))
        sys.exit(1)

    if output_json:
        out = {
            "a": {
                "label": label_a,
                "response": diff.result_a.response.content if diff.result_a.response else "",
                "tokens": diff.result_a.response.total_tokens if diff.result_a.response else 0,
            },
            "b": {
                "label": label_b,
                "response": diff.result_b.response.content if diff.result_b.response else "",
                "tokens": diff.result_b.response.total_tokens if diff.result_b.response else 0,
            },
        }
        click.echo(json.dumps(out, indent=2))
        return

    term_width = shutil.get_terminal_size((120, 40)).columns
    click.echo(format_diff_plain(diff, width=term_width))


# ── prompt validate helpers ────────────────────────────────────────────────────


def _validate_single_file(path: Path) -> bool:
    """Validate one prompt file; print results and return True if valid."""
    try:
        pf = parse_prompt_file(path)
        result = validate_prompt_file(pf)
    except PromptParseError as e:
        _echo_error(f"{path}: {e}")
        return False

    if result.valid and not result.warnings:
        _echo_success(f"✅ {path} — OK")
    elif result.valid:
        click.echo(click.style(f"⚠️  {path} — OK with warnings", fg="yellow"))
        for w in result.warnings:
            click.echo(f"   {w}")
    else:
        click.echo(click.style(f"❌ {path} — INVALID", fg="red"))
        for err in result.errors:
            click.echo(f"   Error: {err}")
        for w in result.warnings:
            click.echo(f"   Warning: {w}")
    return result.valid


# ── prompt validate ─────────────────────────────────────────────────────────────


@cli.command("validate")
@click.argument("prompt_files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def cmd_validate(prompt_files: tuple[Path, ...]) -> None:
    """Validate one or more .prompt files without running them.

    \b
    Examples:
      prompt validate summarize.prompt
      prompt validate prompts/*.prompt
    """
    if not prompt_files:
        click.echo("No files specified.", err=True)
        sys.exit(1)

    all_valid = True
    for path in prompt_files:
        if not _validate_single_file(path):
            all_valid = False
    sys.exit(0 if all_valid else 1)


# ── prompt inspect helpers ──────────────────────────────────────────────────────


def _print_inspect_body(pf: Any, runtime_vars: dict[str, Any]) -> None:
    """Print the rendered or raw prompt body for the inspect command."""
    if runtime_vars or all(not s.required for s in pf.vars.values()):
        click.echo(
            click.style("\n── Resolved Prompt ──────────────────────────────", fg="cyan", bold=True)
        )
        try:
            system, body = render_prompt(pf, runtime_vars)
            if system:
                click.echo(click.style("[system]", fg="blue"))
                click.echo(system)
                click.echo()
            click.echo(click.style("[user]", fg="blue"))
            click.echo(body)
        except PromptRenderError as e:
            _echo_warning(f"Cannot render — {e}")
    else:
        click.echo(
            click.style("\n── Raw Prompt Body ──────────────────────────────", fg="cyan", bold=True)
        )
        click.echo(pf.body)


# ── prompt inspect ──────────────────────────────────────────────────────────────


@cli.command("inspect")
@click.argument("prompt_file", type=click.Path(exists=True, path_type=Path))
@click.option("--var", "vars_list", multiple=True, metavar="KEY=VALUE")
def cmd_inspect(prompt_file: Path, vars_list: tuple[str, ...]) -> None:
    """Show metadata and resolved prompt body without calling LLM.

    \b
    Examples:
      prompt inspect summarize.prompt
      prompt inspect summarize.prompt --var text="Hello world"
    """
    try:
        pf = parse_prompt_file(prompt_file)
        runtime_vars = _parse_vars(vars_list)
    except PromptParseError as e:
        _echo_error(str(e))
        sys.exit(1)

    # Metadata
    click.echo(
        click.style("── Prompt Metadata ──────────────────────────────", fg="cyan", bold=True)
    )
    click.echo(f"  Name        : {pf.name or '(not set)'}")
    click.echo(f"  Description : {pf.description or '(not set)'}")
    click.echo(f"  Provider    : {pf.provider}")
    click.echo(f"  Model       : {pf.model or '(provider default)'}")
    click.echo(f"  Temperature : {pf.temperature}")
    click.echo(f"  Max tokens  : {pf.max_tokens}")

    if pf.vars:
        click.echo("\n  Variables:")
        for name, spec in pf.vars.items():
            default_str = f" = {spec.default!r}" if not spec.required else " (required)"
            click.echo(f"    {{{{ {name} }}}}  — {spec.type}{default_str}")
    else:
        click.echo("  Variables   : none declared")

    _print_inspect_body(pf, runtime_vars)


# ── prompt new helpers ─────────────────────────────────────────────────────────


def _collect_vars_interactively() -> list[str]:
    """Interactively collect variable declarations; return list of YAML var lines."""
    vars_lines: list[str] = []
    click.echo()
    click.echo(click.style("  Variables (Enter blank name to stop):", fg="bright_black"))
    while True:
        var_name = click.prompt("    Variable name", default="").strip()
        if not var_name:
            break
        var_type = click.prompt(
            f"    Type for '{var_name}'",
            type=click.Choice(["string", "int", "float", "bool"], case_sensitive=False),
            default="string",
        )
        var_default = click.prompt("    Default value (blank = required)", default="").strip()
        if var_default:
            vars_lines.append(f"  {var_name}: {var_type} = {var_default}")
        else:
            vars_lines.append(f"  {var_name}: {var_type}")
    return vars_lines


def _build_prompt_content(
    name: str,
    description: str,
    model: str,
    provider: str,
    temperature: float,
    max_tokens: int,
    system: str,
    vars_lines: list[str],
) -> str:
    """Assemble YAML frontmatter + body for a new .prompt file."""
    lines = ["---", f"name: {name}"]
    if description:
        lines.append(f"description: {description}")
    lines += [
        f"model: {model}",
        f"provider: {provider}",
        f"temperature: {temperature}",
        f"max_tokens: {max_tokens}",
    ]
    if system:
        lines.append(f"system: {system}")
    if vars_lines:
        lines.append("vars:")
        lines.extend(vars_lines)
    lines.append("---")
    lines.append("")
    if vars_lines:
        var_names = [v.strip().split(":")[0] for v in vars_lines]
        body_placeholders = " ".join(
            f"{{{{{{{{ {v} }}}}}}}}".replace("{{ ", "{{").replace(" }}", "}}") for v in var_names
        )
        lines.append(f"Write your prompt here. Available variables: {body_placeholders}")
    else:
        lines.append("Write your prompt here.")
    lines.append("")
    return "\n".join(lines)


# ── prompt new ─────────────────────────────────────────────────────────────────

_PROVIDER_DEFAULTS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "ollama": "llama3",
}


@cli.command("new")
@click.argument("output", default="", metavar="[FILE]")
@click.option("--name", default="", help="Prompt name")
@click.option(
    "--provider",
    default="",
    type=click.Choice(["anthropic", "openai", "ollama"], case_sensitive=False),
    help="Provider to use",
)
def cmd_new(output: str, name: str, provider: str) -> None:
    """Scaffold a new .prompt file interactively.

    \b
    Examples:
      prompt new                          # guided, writes to stdout
      prompt new summarize.prompt         # guided, writes to file
      prompt new classify.prompt --provider anthropic
    """
    click.echo(click.style("\n✨ Creating a new .prompt file", fg="cyan", bold=True))
    click.echo(click.style("   Press Enter to accept defaults\n", fg="bright_black"))

    # ── Gather inputs ────────────────────────────────────────────────────────
    if not name:
        # Derive default name from output filename if given
        default_name = Path(output).stem if output else ""
        name = click.prompt("  Prompt name", default=default_name or "my-prompt")

    description = click.prompt("  Description", default="")

    if not provider:
        provider = click.prompt(
            "  Provider",
            type=click.Choice(["anthropic", "openai", "ollama"], case_sensitive=False),
            default="anthropic",
        )

    default_model = _PROVIDER_DEFAULTS.get(provider, "")
    model = click.prompt("  Model", default=default_model)
    temperature = click.prompt("  Temperature", default=0.7)
    max_tokens = click.prompt("  Max tokens", default=1024)
    system = click.prompt("  System prompt (optional)", default="")

    vars_lines = _collect_vars_interactively()
    content = _build_prompt_content(
        name, description, model, provider, temperature, max_tokens, system, vars_lines
    )

    # ── Write or print ───────────────────────────────────────────────────────
    if output:
        dest = Path(output)
        if dest.exists():
            click.confirm(
                click.style(f"\n  {dest} already exists. Overwrite?", fg="yellow"),
                abort=True,
            )
        dest.write_text(content, encoding="utf-8")
        click.echo()
        _echo_success(f"✅ Created {dest}")
        click.echo(click.style(f"   Run it with: prompt run {dest} --var ...", fg="bright_black"))
    else:
        click.echo()
        click.echo(click.style("── Generated .prompt file ──", fg="cyan"))
        click.echo(content)


# ── Entry point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
