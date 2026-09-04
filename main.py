#!/usr/bin/env python3
"""
Semantic Policy Matcher CLI Entry Point.
Algorithmic semantic and morphological prompt-to-policy matching.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

# Auto-activate local .venv if click/rich is missing in the executing Python environment
try:
    import click
    import rich
except ImportError:
    venv_python = BASE_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from semantic_matcher.cli import cli, init_engine
from semantic_matcher.engine.matcher import SemanticMatcher
from semantic_matcher.formatter import format_table


def setup_engine(rebuild: bool = False) -> SemanticMatcher:
    """Convenience helper for programmatic engine initialization."""
    return init_engine(rebuild=rebuild)


if __name__ == "__main__":
    cli()
