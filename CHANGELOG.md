# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- `__version__` now resolved dynamically from installed package metadata via `importlib.metadata` (falls back to `0.1.0` when running from uninstalled source)

### Fixed
- `SECURITY.md` — removed incomplete email contact sentence that had no address

---

## [0.1.0] — 2026-02-26

### Added
- `.prompt` file format: YAML frontmatter + plain-text body with `{{variable}}` placeholders
- `prompt run` — run a `.prompt` file against Anthropic, OpenAI, or Ollama
- `prompt diff` — compare two prompt outputs (or two variable sets) side by side
- `prompt validate` — static check one or more `.prompt` files without calling any LLM
- `prompt inspect` — show metadata and resolved prompt body without calling an LLM
- `prompt new` — interactive wizard to scaffold a new `.prompt` file
- Variable system: typed declarations (`string`, `int`, `float`, `bool`) with optional defaults
- `--dry-run`, `--json`, `--show-prompt` flags for `prompt run`
- `--stream` flag for `prompt run` — streams tokens to stdout as they arrive
- `--stdin-var VAR` flag for `prompt run` — explicitly pipe stdin into a named variable
- Automatic stdin piping for single-required-variable prompts
- `--output FILE` flag to save response to a file
- Override flags: `--model`, `--provider`, `--temperature`, `--max-tokens`, `--system`
- Python library API: `run_prompt_file()`, `stream_run_prompt_file()`, `parse_prompt_file()`, `render_prompt()`
- Providers: `anthropic` (Claude), `openai` (GPT / Azure), `ollama` (local)
- Native streaming via Anthropic `messages.stream()` and OpenAI `stream=True`
- Example prompt files: `summarize`, `translate`, `classify`, `extract-json`
- `py.typed` marker — PEP 561 typed package
- GitHub Actions CI: pytest matrix (Python 3.11, 3.12, 3.13), ruff lint+format, mypy strict
- GitHub issue templates (bug report, feature request) and PR template
- Secret scanning enabled via `.github/secret_scanning.yml`
- `[tool.pytest.ini_options]`, `[tool.mypy]`, and `[tool.ruff]` config in `pyproject.toml`

[Unreleased]: https://github.com/Maneesh-Relanto/Prompt-Run/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Maneesh-Relanto/Prompt-Run/releases/tag/v0.1.0
