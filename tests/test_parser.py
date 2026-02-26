"""Tests for prompt_run.parser"""

import pytest
from prompt_run.parser import (
    parse_prompt_string,
    validate_prompt_file,
    PromptParseError,
)


SIMPLE_PROMPT = """\
---
name: test
provider: anthropic
model: claude-sonnet-4-6
temperature: 0.5
max_tokens: 256
vars:
  text: string
  style: string = bullets
---

Summarize {{text}} as {{style}}.
"""

def test_parse_basic():
    pf = parse_prompt_string(SIMPLE_PROMPT)
    assert pf.name == "test"
    assert pf.provider == "anthropic"
    assert pf.model == "claude-sonnet-4-6"
    assert pf.temperature == pytest.approx(0.5)
    assert pf.max_tokens == 256

def test_parse_vars():
    pf = parse_prompt_string(SIMPLE_PROMPT)
    assert "text" in pf.vars
    assert pf.vars["text"].required is True
    assert "style" in pf.vars
    assert pf.vars["style"].required is False
    assert pf.vars["style"].default == "bullets"

def test_parse_body():
    pf = parse_prompt_string(SIMPLE_PROMPT)
    assert "{{text}}" in pf.body
    assert "{{style}}" in pf.body

def test_template_vars():
    pf = parse_prompt_string(SIMPLE_PROMPT)
    assert pf.template_vars == {"text", "style"}

def test_no_frontmatter():
    raw = "Just a plain prompt with no frontmatter."
    pf = parse_prompt_string(raw)
    assert pf.body == raw
    assert pf.vars == {}

def test_missing_closing_delimiter():
    raw = "---\nname: broken\n\nBody without closing delimiter"
    with pytest.raises(PromptParseError, match="closing"):
        parse_prompt_string(raw)

def test_invalid_yaml():
    raw = "---\nname: [unclosed\n---\nBody"
    with pytest.raises(PromptParseError, match="YAML"):
        parse_prompt_string(raw)

def test_validate_unknown_provider():
    pf = parse_prompt_string(SIMPLE_PROMPT)
    pf.provider = "unknown-llm"
    result = validate_prompt_file(pf)
    assert not result.valid
    assert any("provider" in e for e in result.errors)

def test_validate_empty_body():
    raw = "---\nname: empty\n---\n   "
    pf = parse_prompt_string(raw)
    result = validate_prompt_file(pf)
    assert not result.valid
    assert any("empty" in e for e in result.errors)

def test_validate_undeclared_var_warning():
    raw = "---\nname: test\n---\nHello {{undeclared}}"
    pf = parse_prompt_string(raw)
    result = validate_prompt_file(pf)
    assert result.valid  # warning, not error
    assert any("undeclared" in w for w in result.warnings)

def test_validate_unused_var_warning():
    raw = "---\nname: test\nvars:\n  unused: string\n---\nHello world"
    pf = parse_prompt_string(raw)
    result = validate_prompt_file(pf)
    assert any("unused" in w for w in result.warnings)

def test_system_prompt_parsed():
    raw = "---\nsystem: You are a helpful assistant.\n---\nHello"
    pf = parse_prompt_string(raw)
    assert pf.system == "You are a helpful assistant."

def test_var_type_int():
    raw = "---\nvars:\n  count: int = 5\n---\nCount: {{count}}"
    pf = parse_prompt_string(raw)
    assert pf.vars["count"].type == "int"
    assert pf.vars["count"].default == 5
