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


def test_var_spec_dict_form():
    """Vars declared as a YAML dict with type/default keys."""
    raw = "---\nvars:\n  text:\n    type: string\n    default: hello\n---\n{{text}}"
    pf = parse_prompt_string(raw)
    assert pf.vars["text"].type == "string"
    assert pf.vars["text"].default == "hello"
    assert pf.vars["text"].required is False


def test_var_spec_dict_form_required():
    """Dict-form var with no default is required."""
    raw = "---\nvars:\n  text:\n    type: string\n---\n{{text}}"
    pf = parse_prompt_string(raw)
    assert pf.vars["text"].required is True


def test_var_bare_value():
    """Bare value var like `count: 3` sets type from Python type and is optional."""
    raw = "---\nvars:\n  count: 3\n---\n{{count}} items"
    pf = parse_prompt_string(raw)
    assert pf.vars["count"].required is False
    assert pf.vars["count"].default == 3


def test_parse_no_source_path_empty_name():
    """When parsed from string with no source_path and no name in frontmatter."""
    raw = "---\nprovider: anthropic\n---\nHello"
    pf = parse_prompt_string(raw, source_path=None)
    assert pf.name == ""


def test_validate_max_tokens_zero():
    pf = parse_prompt_string("---\nprovider: anthropic\nmax_tokens: 0\n---\nHello")
    result = validate_prompt_file(pf)
    assert not result.valid
    assert any("max_tokens" in e for e in result.errors)


def test_validate_temperature_out_of_range():
    pf = parse_prompt_string("---\nprovider: anthropic\ntemperature: 3.5\n---\nHello")
    result = validate_prompt_file(pf)
    assert not result.valid
    assert any("temperature" in e for e in result.errors)


def test_var_type_float():
    raw = "---\nvars:\n  ratio: float = 0.5\n---\n{{ratio}}"
    pf = parse_prompt_string(raw)
    assert pf.vars["ratio"].type == "float"
    assert pf.vars["ratio"].default == pytest.approx(0.5)


def test_var_type_bool():
    raw = "---\nvars:\n  flag: bool = true\n---\n{{flag}}"
    pf = parse_prompt_string(raw)
    assert pf.vars["flag"].type == "bool"
    assert pf.vars["flag"].default is True
