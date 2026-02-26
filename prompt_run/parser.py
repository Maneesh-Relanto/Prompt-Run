"""
parser.py
---------
Parses a .prompt file into a PromptFile dataclass.

A .prompt file looks like:

    ---
    name: summarize
    model: claude-sonnet-4-6
    provider: anthropic
    temperature: 0.3
    vars:
      text: string
      style: string = bullets
    ---

    Summarize the following as {{style}}:

    {{text}}

Everything above the second `---` is YAML frontmatter.
Everything below is the prompt body (plain text / Jinja-style).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Data models ────────────────────────────────────────────────────────────────


@dataclass
class VarSpec:
    name: str
    type: str = "string"  # string | int | float | bool
    default: Any = None
    required: bool = True


@dataclass
class PromptFile:
    # Metadata
    name: str = ""
    description: str = ""
    # Provider config
    provider: str = "anthropic"  # anthropic | openai | ollama
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    # Prompts
    system: str = ""
    body: str = ""  # raw body with {{placeholders}}
    # Variables
    vars: dict[str, VarSpec] = field(default_factory=dict)
    # Source
    source_path: Path | None = None

    @property
    def template_vars(self) -> set[str]:
        """Return all {{var}} names found in body and system."""
        pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")
        found = set(pattern.findall(self.body))
        found |= set(pattern.findall(self.system))
        return found


# ── Parsing ────────────────────────────────────────────────────────────────────


class PromptParseError(Exception):
    pass


def _parse_var_spec(name: str, value: Any) -> VarSpec:
    """
    Parse a var declaration from frontmatter.

    Supported forms:
      text: string
      style: string = bullets
      count: int = 3
    """
    if isinstance(value, str):
        # e.g. "string = bullets" or just "string"
        parts = value.split("=", 1)
        var_type = parts[0].strip().lower()
        if len(parts) == 2:
            default_raw = parts[1].strip()
            # Coerce default to declared type
            default = _coerce(default_raw, var_type)
            return VarSpec(name=name, type=var_type, default=default, required=False)
        return VarSpec(name=name, type=var_type, required=True)

    if isinstance(value, dict):
        var_type = str(value.get("type", "string")).lower()
        if "default" in value:
            return VarSpec(
                name=name,
                type=var_type,
                default=_coerce(str(value["default"]), var_type),
                required=False,
            )
        return VarSpec(name=name, type=var_type, required=True)

    # Bare value used directly (e.g. `count: 3`)
    return VarSpec(name=name, type=type(value).__name__, default=value, required=False)


def _coerce(value: str, var_type: str) -> Any:
    """Coerce a string value to the declared type."""
    try:
        if var_type == "int":
            return int(value)
        if var_type == "float":
            return float(value)
        if var_type == "bool":
            return value.lower() in ("true", "1", "yes")
        return value  # string
    except (ValueError, TypeError):
        return value


def parse_prompt_file(path: Path | str) -> PromptFile:
    """
    Parse a .prompt file from disk and return a PromptFile.
    """
    path = Path(path)
    if not path.exists():
        raise PromptParseError(f"File not found: {path}")

    raw = path.read_text(encoding="utf-8")
    return parse_prompt_string(raw, source_path=path)


def parse_prompt_string(raw: str, source_path: Path | None = None) -> PromptFile:
    """
    Parse the raw content of a .prompt file.
    Splits on `---` delimiters to separate frontmatter from body.
    """
    # Split into frontmatter + body
    # Allow optional leading `---`
    stripped = raw.strip()

    if stripped.startswith("---"):
        # Remove the opening ---
        rest = stripped[3:]
        # Find the closing ---
        close = rest.find("\n---")
        if close == -1:
            raise PromptParseError(
                "Invalid .prompt file: found opening `---` but no closing `---`.\n"
                "Make sure your frontmatter is wrapped with `---` on both sides."
            )
        frontmatter_raw = rest[:close].strip()
        body = rest[close + 4 :].strip()  # skip past \n---
    else:
        # No frontmatter — just a bare prompt body
        frontmatter_raw = ""
        body = stripped

    # Parse YAML frontmatter
    try:
        meta: dict[str, Any] = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as e:
        raise PromptParseError(f"Invalid YAML in frontmatter:\n{e}") from e

    if not isinstance(meta, dict):
        raise PromptParseError("Frontmatter must be a YAML mapping (key: value pairs).")

    # Parse vars block
    vars_raw: dict[str, Any] = meta.get("vars", {}) or {}
    vars_parsed: dict[str, VarSpec] = {}
    for var_name, var_val in vars_raw.items():
        vars_parsed[var_name] = _parse_var_spec(var_name, var_val)

    pf = PromptFile(
        name=str(meta.get("name", source_path.stem if source_path else "")),
        description=str(meta.get("description", "")),
        provider=str(meta.get("provider", "anthropic")).lower(),
        model=str(meta.get("model", "")),
        temperature=float(meta.get("temperature", 0.7)),
        max_tokens=int(meta.get("max_tokens", 1024)),
        system=str(meta.get("system", "")),
        body=body,
        vars=vars_parsed,
        source_path=source_path,
    )

    # Validate: warn if body uses vars not declared in frontmatter
    undeclared = pf.template_vars - set(pf.vars.keys())
    if undeclared:
        # Not a hard error — user might pass them via --var anyway
        # We surface this in `prompt validate`
        pass

    return pf


# ── Validation ─────────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


KNOWN_PROVIDERS = {"anthropic", "openai", "ollama"}


def validate_prompt_file(pf: PromptFile) -> ValidationResult:
    """
    Run static checks on a parsed PromptFile.
    Returns a ValidationResult with errors and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Provider check
    if pf.provider not in KNOWN_PROVIDERS:
        errors.append(
            f"Unknown provider `{pf.provider}`. Supported: {', '.join(sorted(KNOWN_PROVIDERS))}"
        )

    # Temperature range
    if not (0.0 <= pf.temperature <= 2.0):
        errors.append(f"temperature must be between 0.0 and 2.0, got {pf.temperature}")

    # max_tokens sanity
    if pf.max_tokens < 1:
        errors.append(f"max_tokens must be >= 1, got {pf.max_tokens}")

    # Body must not be empty
    if not pf.body.strip():
        errors.append("Prompt body is empty — nothing to send to the model.")

    # Undeclared vars used in body
    undeclared = pf.template_vars - set(pf.vars.keys())
    if undeclared:
        warnings.append(
            f"Variable(s) used in body but not declared in frontmatter: "
            f"{', '.join(sorted(undeclared))}. "
            f"Pass them via --var at runtime."
        )

    # Declared vars not used in body or system
    unused = set(pf.vars.keys()) - pf.template_vars
    if unused:
        warnings.append(
            f"Variable(s) declared in frontmatter but never used in body: "
            f"{', '.join(sorted(unused))}."
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
