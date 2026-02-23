"""
prompt-run
----------
A universal CLI runner for .prompt files.
Treat prompts as first-class files.
"""

from .parser import parse_prompt_file, parse_prompt_string, validate_prompt_file, PromptFile
from .renderer import render_prompt
from .runner import run_prompt_file, run_prompt_string, stream_run_prompt_file, RunConfig, RunResult
from .providers import get_provider, PROVIDERS

__version__ = "0.1.0"
__all__ = [
    "parse_prompt_file",
    "parse_prompt_string",
    "validate_prompt_file",
    "render_prompt",
    "run_prompt_file",
    "run_prompt_string",
    "stream_run_prompt_file",
    "RunConfig",
    "RunResult",
    "PromptFile",
    "get_provider",
    "PROVIDERS",
]
