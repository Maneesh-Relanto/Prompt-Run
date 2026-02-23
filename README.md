# prompt-run

**curl for prompts.** Run `.prompt` files against any LLM from the terminal.

[![CI](https://github.com/Maneesh-Relanto/Prompt-Run/actions/workflows/ci.yml/badge.svg)](https://github.com/Maneesh-Relanto/Prompt-Run/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/prompt-run)](https://pypi.org/project/prompt-run/)
[![Python](https://img.shields.io/pypi/pyversions/prompt-run)](https://pypi.org/project/prompt-run/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-cc785c?logo=anthropic&logoColor=white)](https://www.anthropic.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)](https://platform.openai.com)
[![Ollama](https://img.shields.io/badge/Ollama-local-3d8bcd?logo=ollama&logoColor=white)](https://ollama.com)

Prompts are code. Treat them like it.

```bash
prompt run summarize.prompt --var text="$(cat article.txt)"
prompt diff v1.prompt v2.prompt --var text="same input"
prompt validate prompts/*.prompt
```

---

## Why?

Every team building with LLMs ends up with the same mess — prompts buried in Python strings, Notion docs, and Slack threads. No history. No review. No way to test them.

**prompt-run fixes this by giving prompts a home: `.prompt` files.**

- ✅ Committed alongside code in git
- ✅ Reviewed in PRs like any other file
- ✅ Swappable across models and providers without touching application code
- ✅ Runnable from the terminal or CI with one command

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
```bash
export ANTHROPIC_API_KEY="sk-..."   # for Anthropic
export OPENAI_API_KEY="sk-..."      # for OpenAI
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

Checks:
- Valid YAML frontmatter
- Known provider name
- Temperature in valid range
- Body is not empty
- Variables used in body are declared
- Declared variables are actually used

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
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
prompt run my.prompt --provider anthropic --model claude-sonnet-4-6
```

### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
prompt run my.prompt --provider openai --model gpt-4o
```

### Ollama (local, no key needed)
```bash
ollama serve          # in another terminal
ollama pull llama3
prompt run my.prompt --provider ollama --model llama3
```

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT
