# Contributing to prompt-run

Thanks for your interest! This guide gets you set up fast.

## Setup

```bash
git clone https://github.com/Maneesh-Relanto/Prompt-Run
cd Prompt-Run
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -v
```

## Adding a new provider

1. Create `prompt_run/providers/yourprovider.py` implementing `BaseProvider`
2. Add it to the `PROVIDERS` dict in `prompt_run/providers/__init__.py`
3. Add tests in `tests/`
4. Document it in `README.md`

## File structure

```
prompt_run/
  cli.py         ← Click CLI entry point
  parser.py      ← .prompt file parsing
  renderer.py    ← {{variable}} substitution
  runner.py      ← parse → render → call orchestration
  diff.py        ← side-by-side comparison
  providers/
    base.py      ← abstract provider interface
    anthropic.py
    openai.py
    ollama.py
tests/           ← pytest tests
examples/        ← example .prompt files
```

## Pull requests

- Keep PRs focused — one feature or fix per PR
- Add tests for new behaviour
- Run `prompt validate examples/*.prompt` before submitting
