# Contributing to prompt-run

First off — thank you! prompt-run is an open project and every contribution matters, whether it's a bug report, a new provider, a typo fix, or a new example prompt.

---

## Table of contents

- [Quick start](#quick-start)
- [Project structure](#project-structure)
- [Running tests](#running-tests)
- [Lint and type checking](#lint-and-type-checking)
- [Good first issues](#good-first-issues)
- [Adding a new provider](#adding-a-new-provider)
- [Adding example prompts](#adding-example-prompts)
- [Pull request checklist](#pull-request-checklist)
- [Code style](#code-style)
- [Reporting bugs](#reporting-bugs)

---

## Quick start

```bash
git clone https://github.com/Maneesh-Relanto/Prompt-Run
cd Prompt-Run
pip install -e ".[dev]"
```

Or with `make`:

```bash
make install   # installs in editable mode with dev deps
make test      # run the full test suite
make lint      # ruff + mypy
```

---

## Project structure

```
prompt_run/
  __init__.py    ← public API: run_prompt_file, parse_prompt_file, render_prompt
  cli.py         ← Click CLI entry point (prompt run / diff / validate / inspect / new)
  parser.py      ← .prompt file parsing → PromptFile dataclass
  renderer.py    ← {{variable}} substitution with type coercion
  runner.py      ← orchestrates parse → render → provider call → RunResult
  diff.py        ← side-by-side comparison logic
  providers/
    base.py      ← abstract BaseProvider + ProviderResponse dataclass
    anthropic.py ← Anthropic Claude (streaming + buffered)
    openai.py    ← OpenAI / Azure (streaming + buffered)
    ollama.py    ← Ollama local models (HTTP)
tests/
  conftest.py        ← shared fixtures
  test_parser.py     ← parser unit tests
  test_renderer.py   ← renderer unit tests
  test_cli.py        ← CLI integration tests (using Click test runner)
examples/
  summarize.prompt   ← summarize text into bullet points
  translate.prompt   ← translate text to any language
  classify.prompt    ← classify text into categories
  extract-json.prompt ← extract structured JSON from text
```

---

## Running tests

```bash
pytest                     # run everything
pytest tests/test_parser.py -v        # single file
pytest -k "test_dry_run"   # single test by keyword
pytest --tb=short -q       # compact output (same as CI)
```

Tests never call real LLM APIs — providers are mocked. No API key needed.

---

## Lint and type checking

```bash
make lint        # ruff check + ruff format check + mypy
make format      # auto-fix formatting with ruff
```

Or run manually:

```bash
ruff check .
ruff format --check .
mypy prompt_run --ignore-missing-imports
```

---

## Good first issues

These are well-scoped, self-contained tasks — great for a first contribution:

| # | Task | Effort |
|---|---|---|
| 1 | **Add Google Gemini provider** — implement `GeminiProvider` using `google-generativeai` SDK | ~60 lines |
| 2 | **Add Groq provider** — implement `GroqProvider` using OpenAI-compatible SDK | ~40 lines |
| 3 | **Add `prompt list` command** — scan a directory and print all `.prompt` files found with name/description | ~30 lines |
| 4 | **Add `--watch` flag to `prompt run`** — re-run prompt on file change using `watchfiles` | ~20 lines |
| 5 | **Add Mistral provider** — implement using `mistralai` SDK | ~60 lines |
| 6 | **More example `.prompt` files** — code review, SQL generation, meeting notes, etc. | ~10 lines each |
| 7 | **Windows CI** — add `windows-latest` to the GitHub Actions matrix | ~5 lines |
| 8 | **`prompt run --repeat N`** — run same prompt N times and show all outputs | ~25 lines |

Open a GitHub issue before starting on a larger item so we can align on design.

---

## Adding a new provider

All providers live in `prompt_run/providers/` and implement `BaseProvider`:

```python
# prompt_run/providers/myprovider.py
from .base import BaseProvider, ProviderResponse, ProviderError
from typing import Iterator

class MyProvider(BaseProvider):
    name = "myprovider"

    def __init__(self):
        # import SDK, read API key from env, raise ProviderError if missing
        ...

    def default_model(self) -> str:
        return "my-default-model"

    def complete(self, system, prompt, model, temperature, max_tokens) -> ProviderResponse:
        # call API, return ProviderResponse(content, model, provider, input_tokens, output_tokens, total_tokens)
        ...

    def stream_complete(self, system, prompt, model, temperature, max_tokens) -> Iterator[str]:
        # yield text chunks; if streaming is unsupported, call super().stream_complete(...)
        ...
```

Then register it in `prompt_run/providers/__init__.py`:

```python
from .myprovider import MyProvider
PROVIDERS: dict[str, type[BaseProvider]] = {
    ...
    "myprovider": MyProvider,
}
```

Add `myprovider` to the provider choices in `pyproject.toml` optional dependencies, write tests, and document in README.

---

## Adding example prompts

Example `.prompt` files live in `examples/`. A good example:
- Has a clear `name` and `description` in frontmatter
- Uses at least one `{{variable}}`
- Works with the default provider (anthropic) without extra setup
- Shows a non-trivial but universally useful use case

After adding, run:

```bash
prompt validate examples/*.prompt
```

And add a row to the Examples table in `README.md`.

---

## Pull request checklist

Before submitting, ensure:

- [ ] `make test` passes locally
- [ ] `make lint` passes (no ruff or mypy errors)
- [ ] `prompt validate examples/*.prompt` passes
- [ ] New behaviour has tests in `tests/`
- [ ] New provider has a section in `README.md`
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]`
- [ ] PR title is concise and imperative ("Add Gemini provider", not "Added gemini")

---

## Code style

- Python 3.11+, fully typed (`mypy --strict`)
- Line length: 100 (configured in `pyproject.toml`)
- Formatter: `ruff format`
- Linter: `ruff check`
- No external dependencies beyond `click` and `pyyaml` in core; provider SDKs are optional extras
- Prefer dataclasses over dicts for structured return values
- Raise `ProviderError`, `PromptParseError`, or `PromptRenderError` — never raw `Exception`

---

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:
- Your OS and Python version
- The `.prompt` file content (redact any sensitive data)
- The exact command you ran
- The full error output

---

## Questions?

Open a [GitHub Discussion](https://github.com/Maneesh-Relanto/Prompt-Run/discussions) — issues are for bugs and feature requests, discussions are for everything else.
