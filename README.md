# prompt-run

**curl for prompts.** Run `.prompt` files against any LLM from the terminal.

[![CI](https://img.shields.io/github/actions/workflow/status/Maneesh-Relanto/Prompt-Run/ci.yml?branch=main&style=flat-square&label=CI&color=16a34a&logo=github-actions&logoColor=white)](https://github.com/Maneesh-Relanto/Prompt-Run/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/prompt-run?style=flat-square&color=0284c7&logo=pypi&logoColor=white)](https://pypi.org/project/prompt-run/)
[![PyPI Downloads](https://img.shields.io/badge/downloads%2Fmo-TBU-0284c7?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/prompt-run/)
[![Python](https://img.shields.io/pypi/pyversions/prompt-run?style=flat-square&color=7c3aed&logo=python&logoColor=white)](https://pypi.org/project/prompt-run/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-22c55e?style=flat-square)](https://github.com/Maneesh-Relanto/Prompt-Run)
[![License: MIT](https://img.shields.io/badge/license-MIT-f59e0b?style=flat-square)](LICENSE)

[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-b45309?style=flat-square&logo=anthropic&logoColor=white)](https://www.anthropic.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-6d28d9?style=flat-square&logo=openai&logoColor=white)](https://platform.openai.com)
[![Ollama](https://img.shields.io/badge/Ollama-local-0f766e?style=flat-square&logo=ollama&logoColor=white)](https://ollama.com)

[![No Telemetry](https://img.shields.io/badge/telemetry-none-22c55e?style=flat-square&logo=checkmarx&logoColor=white)](#privacy--security)
[![No Data Stored](https://img.shields.io/badge/data%20stored-none-22c55e?style=flat-square&logo=checkmarx&logoColor=white)](#privacy--security)
[![Runs 100% Local](https://img.shields.io/badge/runs-100%25%20local-0ea5e9?style=flat-square&logo=homeassistant&logoColor=white)](#privacy--security)
[![No Account Required](https://img.shields.io/badge/account-not%20required-0ea5e9?style=flat-square&logo=checkmarx&logoColor=white)](#privacy--security)

Prompts are code. Treat them like it.

---

## Table of contents

- [Privacy & Security](#-privacy--security)
- [Quick start](#quick-start)
- [Why?](#why)
- [Why not LangChain / promptfoo / Langfuse?](#why-not-langchain--promptfoo--langfuse)
- [Install](#install)
- [The `.prompt` file format](#the-prompt-file-format)
- [Commands](#commands)
  - [`prompt new`](#prompt-new)
  - [`prompt run`](#prompt-run)
  - [`prompt diff`](#prompt-diff)
  - [`prompt validate`](#prompt-validate)
  - [`prompt inspect`](#prompt-inspect)
- [Use as a Python library](#use-as-a-python-library)
- [Provider setup](#provider-setup)
- [Use in CI / GitHub Actions](#use-in-ci--github-actions)
- [Examples](#examples)
- [Development setup](#development-setup)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Security](#security)
- [License](#license)

---

## 🔒 Privacy & Security

> **prompt-run runs entirely on your machine.** It is a local CLI tool with no backend, no telemetry, and no cloud component of its own.

| | |
|---|---|
| **API keys** | Read from environment variables, passed directly to your chosen provider. Never stored, logged, or sent anywhere else. |
| **Prompts & outputs** | Stay on your machine. The only server that sees them is the AI provider you explicitly call. |
| **Telemetry** | None. Zero usage data, no crash reports, no background calls, no tracking of any kind. |
| **Accounts** | Not required. There is no prompt-run account or sign-up. |

When you run `prompt run`, the only network traffic is the request you intentionally send to your chosen AI provider.

---

## Quick start

**1. Install**
```bash
pip install "prompt-run[anthropic]"
export ANTHROPIC_API_KEY="sk-ant-..."
```

**2. Run an example prompt from this repo**
```bash
prompt run examples/summarize.prompt --var text="LLMs are changing how developers build software."
```

**3. Try streaming, dry-run, and diff**
```bash
# Stream tokens as they arrive
prompt run examples/summarize.prompt --var text="Your text here" --stream

# Preview the resolved prompt without calling the LLM
prompt run examples/summarize.prompt --var text="Your text here" --dry-run

# Compare two inputs side by side
prompt diff examples/summarize.prompt \
  --a-var text="First article content..." \
  --b-var text="Second article content..."
```

**4. Write your own**
```bash
prompt new my-prompt.prompt       # interactive wizard
prompt run my-prompt.prompt --var input="hello"
```

That's it. No config files, no accounts, no platform.

---

## Why?

Every team building with LLMs ends up with the same mess — prompts buried in Python strings, Notion docs, and Slack threads. No history. No review. No way to test them.

**prompt-run fixes this by giving prompts a home: `.prompt` files.**

- ✅ Committed alongside code in git
- ✅ Reviewed in PRs like any other file
- ✅ Swappable across models and providers without touching application code
- ✅ Runnable from the terminal or CI with one command

---

## Why not LangChain / promptfoo / Langfuse?

| | **prompt-run** | LangChain | promptfoo | Langfuse |
|---|---|---|---|---|
| Prompt format | Plain `.prompt` file | Python code | YAML config | Web UI / SDK |
| Works in terminal | ✅ | ❌ | ✅ | ❌ |
| Works as Python library | ✅ | ✅ | ❌ | ✅ |
| No framework lock-in | ✅ | ❌ | ✅ | ❌ |
| Diff two prompt outputs | ✅ | ❌ | Partial (web UI) | ❌ |
| Pipe stdin / shell-friendly | ✅ | ❌ | ❌ | ❌ |
| Works offline (Ollama) | ✅ | ✅ | ✅ | ❌ |
| Zero config beyond API key | ✅ | ❌ | ❌ | ❌ |
| Prompt lives in git | ✅ | Partial | ✅ | Partial |

prompt-run is a **single-purpose tool** — it does one thing well and stays out of your stack. No agents, no chains, no platform.

---

## Install

```bash
pip install prompt-run

# With provider SDKs (pick what you need):
pip install "prompt-run[anthropic]"   # Anthropic Claude
pip install "prompt-run[openai]"      # OpenAI / Azure
pip install "prompt-run[all]"         # Everything
```

Set your API key:

**macOS / Linux**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # for Anthropic
export OPENAI_API_KEY="sk-..."          # for OpenAI
# Ollama needs no key — just run `ollama serve`
```

**Windows (PowerShell)**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # for Anthropic
$env:OPENAI_API_KEY = "sk-..."          # for OpenAI
# Ollama needs no key — just run `ollama serve`
```

---

## The `.prompt` file format

A `.prompt` file has two parts: YAML frontmatter and a plain text body.

```
---
name: summarize
description: Summarizes text into bullet points
model: claude-sonnet-4-6
provider: anthropic
temperature: 0.3
max_tokens: 512
vars:
  text: string
  style: string = bullet points
  max_bullets: int = 5
---

Summarize the following text as {{style}}.
Use no more than {{max_bullets}} bullets.

Text:
{{text}}
```

Variables use `{{double braces}}`. Defaults are declared in frontmatter. Everything is overridable at the CLI.

### Frontmatter reference

| Field         | Type   | Default      | Description                              |
|---------------|--------|--------------|------------------------------------------|
| `name`        | string | filename     | Human name for this prompt               |
| `description` | string | —            | What this prompt does                    |
| `provider`    | string | `anthropic`  | `anthropic` / `openai` / `ollama`        |
| `model`       | string | provider default | Model to use                         |
| `temperature` | float  | `0.7`        | Randomness (0.0–2.0)                     |
| `max_tokens`  | int    | `1024`       | Max output tokens                        |
| `system`      | string | —            | System prompt                            |
| `vars`        | map    | —            | Variable declarations with types/defaults|

### Variable types

```yaml
vars:
  text: string          # required string
  count: int = 5        # optional int, defaults to 5
  verbose: bool = false # optional bool
  ratio: float = 0.5    # optional float
```

---

## Commands

### `prompt new`

Scaffold a new `.prompt` file interactively — no YAML knowledge needed.

```bash
prompt new                      # guided wizard, prints to stdout
prompt new summarize.prompt     # guided wizard, writes to file
```

You'll be asked for name, description, provider, model, temperature, and variables. The file is ready to run immediately.

---

### `prompt run`

Run a `.prompt` file against an LLM.

```bash
# Basic
prompt run summarize.prompt --var text="Hello world"

# Multiple vars
prompt run translate.prompt --var text="Bonjour" --var target_lang=English

# Override model/provider at runtime
prompt run summarize.prompt --model gpt-4o --provider openai

# Pipe stdin (auto-detected for single required var)
cat article.txt | prompt run summarize.prompt

# Stream tokens as they arrive
prompt run summarize.prompt --var text="test" --stream

# Save response to a file
prompt run summarize.prompt --var text="test" --output summary.txt

# Preview the resolved prompt without sending
prompt run summarize.prompt --var text="test" --dry-run

# Get JSON output with metadata
prompt run summarize.prompt --var text="test" --json
```

**Flags**

| Flag | Description |
|------|-------------|
| `--var KEY=VALUE` | Pass a variable (repeatable) |
| `--model MODEL` | Override model |
| `--provider PROVIDER` | Override provider |
| `--temperature FLOAT` | Override temperature |
| `--max-tokens INT` | Override max tokens |
| `--system TEXT` | Override system prompt |
| `--stream` | Stream tokens to stdout as they arrive |
| `--stdin-var VAR` | Pipe stdin into a specific variable |
| `--output FILE` | Write response to file instead of stdout |
| `--dry-run` | Print resolved prompt, don't call LLM |
| `--json` | Return JSON with response + token metadata |
| `--show-prompt` | Print resolved prompt before response |

---

### `prompt diff`

Run a prompt with two different inputs and compare outputs side by side.

```bash
# Same prompt, two different inputs
prompt diff summarize.prompt \
  --a-var text="First article content here..." \
  --b-var text="Second article content here..."

# Two prompt versions, same input (A/B testing a prompt change)
prompt diff prompts/v1/summarize.prompt prompts/v2/summarize.prompt \
  --var text="$(cat article.txt)"
```

Output:
```
┌─ v1/summarize.prompt ──────────┬─ v2/summarize.prompt ──────────┐
│ • The company reported record  │ 1. Record quarterly revenue of  │
│   revenue this quarter.        │    $2.1B, up 14% YoY.           │
│ • Growth was driven by cloud   │ 2. Cloud services drove growth, │
│   services.                    │    up 32%.                       │
└────────────────────────────────┴────────────────────────────────┘
  Tokens — A: 312 in / 48 out | B: 318 in / 61 out
```

---

### `prompt validate`

Static check one or more `.prompt` files without calling any LLM.

```bash
prompt validate summarize.prompt
prompt validate prompts/*.prompt   # glob support
```

Checks (these are **errors** — validation fails):
- Valid YAML frontmatter
- Known provider name (`anthropic`, `openai`, `ollama`)
- Temperature in range `0.0–2.0`
- Body is not empty
- `max_tokens` is at least 1

Checks (these are **warnings** — validation passes with a note):
- Variables used in body but not declared in frontmatter
- Variables declared in frontmatter but never used in body

---

### `prompt inspect`

Show metadata and the fully-resolved prompt body.

```bash
prompt inspect summarize.prompt
prompt inspect summarize.prompt --var text="Hello world"
```

---

## Use as a Python library

```python
from prompt_run import run_prompt_file, RunConfig

config = RunConfig(
    vars={"text": "My article content here..."},
    model="claude-sonnet-4-6",
)

result = run_prompt_file("summarize.prompt", config)
print(result.response.content)
print(result.response.token_summary)
```

Parse and render without calling LLM:

```python
from prompt_run import parse_prompt_file, render_prompt

pf = parse_prompt_file("summarize.prompt")
system, body = render_prompt(pf, {"text": "hello"})
print(body)
```

---

## Provider setup

### Anthropic (default)

**macOS / Linux**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
**Windows (PowerShell)**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```
```bash
prompt run my.prompt --provider anthropic --model claude-sonnet-4-6
```

### OpenAI

**macOS / Linux**
```bash
export OPENAI_API_KEY="sk-..."
```
**Windows (PowerShell)**
```powershell
$env:OPENAI_API_KEY = "sk-..."
```
```bash
prompt run my.prompt --provider openai --model gpt-4o
```

### Ollama (local, no key needed)
```bash
ollama serve          # in another terminal
ollama pull llama3
prompt run my.prompt --provider ollama --model llama3
```

> **Tip — persist API keys across sessions:** Add the `export` lines to your `~/.bashrc`, `~/.zshrc`, or `$PROFILE` (PowerShell) so you don't need to set them each time.

---

## Use in CI / GitHub Actions

```yaml
- name: Validate all prompts
  run: prompt validate prompts/*.prompt

- name: Test prompt output
  run: |
    output=$(prompt run prompts/classify.prompt \
      --var text="I love this product!" \
      --var categories="positive,negative,neutral")
    echo "Classification: $output"
```

---

## Examples

The `examples/` folder contains ready-to-run `.prompt` files:

| File | Description |
|------|-------------|
| [summarize.prompt](examples/summarize.prompt) | Summarize text into bullet points |
| [translate.prompt](examples/translate.prompt) | Translate text to any language |
| [classify.prompt](examples/classify.prompt) | Classify text into categories |
| [extract-json.prompt](examples/extract-json.prompt) | Extract structured JSON from text |

---

## Development setup

Everything you need to go from zero to running tests locally.

### Prerequisites

- Python 3.11 or later — [python.org/downloads](https://www.python.org/downloads/)
- git
- (Optional) [make](https://www.gnu.org/software/make/) — convenience wrapper; all commands also work without it

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/Maneesh-Relanto/Prompt-Run
cd Prompt-Run
```

---

### Step 2 — Create a virtual environment

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

### Step 3 — Install in editable mode with dev dependencies

```bash
pip install -e ".[dev]"
# or
make install
```

This installs:
- `prompt-run` itself in editable mode (changes to source take effect immediately)
- `pytest`, `pytest-cov` for testing
- `anthropic` and `openai` SDKs (used in tests via mocks — no API key needed)
- `types-PyYAML` for mypy

---

### Step 4 — Run the test suite

```bash
pytest                          # run all 113 tests
pytest -v                       # verbose output
pytest tests/test_parser.py     # single module
pytest -k "test_dry_run"        # filter by name
pytest --tb=short -q            # compact (same as CI)

# or
make test
```

> Tests never call real LLM APIs — all providers are fully mocked. No API key required.

---

### Step 5 — Lint and type-check

```bash
make lint       # ruff check + ruff format --check + mypy --strict
make format     # auto-fix formatting with ruff
```

Or manually:
```bash
ruff check .
ruff format --check .
mypy prompt_run --ignore-missing-imports
```

---

### Step 6 — Validate example prompts

```bash
prompt validate examples/*.prompt
```

All four examples should pass with no errors.

---

### Step 7 — Make your change, then verify everything passes

```bash
make test        # all tests pass
make lint        # no ruff or mypy errors
prompt validate examples/*.prompt   # example prompts still valid
```

Then open a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full PR checklist, good first issues, and how to add a new provider.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full history of releases and changes.

---

## Security

See [SECURITY.md](SECURITY.md) for the supported versions and vulnerability reporting policy.

---

## License

MIT
