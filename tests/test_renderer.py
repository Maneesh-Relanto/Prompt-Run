"""Tests for prompt_run.renderer"""

import pytest
from prompt_run.parser import parse_prompt_string
from prompt_run.renderer import render_prompt, resolve_vars, PromptRenderError


PROMPT = """\
---
vars:
  text: string
  style: string = bullets
  count: int = 3
---
Summarize {{text}} as {{style}}. Max {{count}} items.
"""

def test_render_with_all_vars():
    pf = parse_prompt_string(PROMPT)
    _, body = render_prompt(pf, {"text": "Hello world", "style": "numbered"})
    assert "Hello world" in body
    assert "numbered" in body

def test_render_uses_default():
    pf = parse_prompt_string(PROMPT)
    _, body = render_prompt(pf, {"text": "My text"})
    assert "bullets" in body   # style default
    assert "3" in body          # count default

def test_render_missing_required_var():
    pf = parse_prompt_string(PROMPT)
    with pytest.raises(PromptRenderError, match="text"):
        render_prompt(pf, {})

def test_render_int_coercion():
    pf = parse_prompt_string(PROMPT)
    _, body = render_prompt(pf, {"text": "Hi", "count": "7"})
    assert "7" in body

def test_render_unknown_var_passthrough():
    pf = parse_prompt_string(PROMPT)
    # Extra var not in schema — passes through fine
    _, body = render_prompt(pf, {"text": "Hi", "extra": "ignored"})
    assert "Hi" in body

def test_render_system_prompt():
    raw = "---\nsystem: You are {{role}}.\nvars:\n  role: string\n---\nHello"
    pf = parse_prompt_string(raw)
    system, _ = render_prompt(pf, {"role": "an assistant"})
    assert system == "You are an assistant."

def test_render_no_vars():
    raw = "---\nname: static\n---\nThis is a static prompt."
    pf = parse_prompt_string(raw)
    _, body = render_prompt(pf, {})
    assert body == "This is a static prompt."

def test_render_bad_int_coercion():
    raw = "---\nvars:\n  n: int\n---\n{{n}} items"
    pf = parse_prompt_string(raw)
    with pytest.raises(PromptRenderError, match="int"):
        render_prompt(pf, {"n": "not-a-number"})
