"""
renderer.py
-----------
Resolves {{variable}} placeholders in a PromptFile body and system prompt.

Rules:
  - {{var}} is replaced with the runtime value
  - Missing required vars raise PromptRenderError with a clear message
  - Missing optional vars use their declared default
  - Type coercion happens at render time
  - Unknown vars passed at runtime are ignored (not an error)
"""

from __future__ import annotations

import re
import sys
from typing import Any

from .parser import PromptFile, VarSpec


class PromptRenderError(Exception):
    pass


PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _coerce_value(value: Any, spec: VarSpec) -> Any:
    """Coerce a runtime string value to the declared type."""
    if not isinstance(value, str):
        return value
    t = spec.type.lower()
    try:
        if t == "int":
            return int(value)
        if t == "float":
            return float(value)
        if t == "bool":
            return value.lower() in ("true", "1", "yes")
        return value
    except (ValueError, TypeError):
        raise PromptRenderError(
            f"Cannot convert value '{value}' to type '{t}' for variable '{spec.name}'."
        )


def _find_missing_vars(
    pf: PromptFile,
    resolved: dict[str, Any],
) -> list[str]:
    """Return template variables that are required but absent from resolved."""
    missing = []
    for var_name in pf.template_vars:
        if var_name not in resolved:
            spec = pf.vars.get(var_name)
            if (spec and spec.required) or var_name not in pf.vars:
                missing.append(var_name)
    return missing


def resolve_vars(
    pf: PromptFile,
    runtime_vars: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge declared defaults with runtime values.
    Raises PromptRenderError if a required variable is missing.
    Returns fully-resolved variable dict.
    """
    resolved: dict[str, Any] = {}

    # Start with defaults from declared vars
    for name, spec in pf.vars.items():
        if not spec.required:
            resolved[name] = spec.default

    # Override with runtime values (with type coercion)
    for name, value in runtime_vars.items():
        spec_opt = pf.vars.get(name)
        if spec_opt:
            resolved[name] = _coerce_value(value, spec_opt)
        else:
            # Undeclared var — pass through as string
            resolved[name] = value

    # Check all template vars in body are accounted for
    missing = _find_missing_vars(pf, resolved)

    if missing:
        raise PromptRenderError(
            f"Missing required variable(s): {', '.join(sorted(missing))}.\n"
            f"Pass them with: " + " ".join(f'--var {m}="..."' for m in sorted(missing))
        )

    return resolved


def render_template(template: str, variables: dict[str, Any]) -> str:
    """
    Replace all {{var}} occurrences in template with resolved values.
    Unresolved placeholders that remain after substitution are left as-is
    (they were already caught in resolve_vars).
    """

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        return str(match.group(0))  # leave unresolved placeholder as-is

    return PLACEHOLDER_RE.sub(replacer, template)


def render_prompt(
    pf: PromptFile,
    runtime_vars: dict[str, Any],
) -> tuple[str, str]:
    """
    Fully render a PromptFile with runtime variables.

    Returns:
        (rendered_system, rendered_body)
    """
    resolved = resolve_vars(pf, runtime_vars)
    rendered_body = render_template(pf.body, resolved)
    rendered_system = render_template(pf.system, resolved) if pf.system else ""
    return rendered_system, rendered_body


def read_stdin_if_piped() -> str | None:
    """Return stdin content if data is being piped in, else None."""
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return None
