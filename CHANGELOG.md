# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `--stream` flag for `prompt run` — streams tokens to stdout as they arrive
  (Anthropic and OpenAI providers; Ollama falls back to buffered output)
- `--stdin-var VAR` flag for `prompt run` — explicitly pipe stdin into a named variable
- Native streaming support in `AnthropicProvider` via `messages.stream()`
- Native streaming support in `OpenAIProvider` via `stream=True`
- `stream_run_prompt_file()` public API for library consumers
- `py.typed` marker — prompt-run is now PEP 561 typed
- GitHub Actions CI workflow with matrix testing (Python 3.11, 3.12)
- GitHub issue templates (bug report, feature request) and PR template
- `[tool.pytest.ini_options]`, `[tool.mypy]`, and `[tool.ruff]` config in `pyproject.toml`

---

## [0.1.0] — 2026-02-24

### Added
- `.prompt` file format: YAML frontmatter + plain-text body with `{{variable}}` placeholders
- `prompt run` — run a `.prompt` file against Anthropic, OpenAI, or Ollama
- `prompt diff` — compare two prompt outputs (or two variable sets) side by side
- `prompt validate` — static check one or more `.prompt` files without calling any LLM
- `prompt inspect` — show metadata and resolved prompt body without calling an LLM
- Variable system: typed declarations (`string`, `int`, `float`, `bool`) with optional defaults
- `--dry-run`, `--json`, `--show-prompt` flags for `prompt run`
- Automatic stdin piping for single-required-variable prompts
- Python library API: `run_prompt_file()`, `parse_prompt_file()`, `render_prompt()`
- Providers: `anthropic` (Claude), `openai` (GPT / Azure), `ollama` (local)
- Example prompt files: `summarize`, `translate`, `classify`, `extract-json`

[Unreleased]: https://github.com/maneesh-thakur/prompt-run/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maneesh-thakur/prompt-run/releases/tag/v0.1.0
