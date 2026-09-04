"""
Semantic Policy Matcher
Algorithmic semantic & morphological policy matcher for natural language prompts.
"""

__version__ = "0.2.0"

from .cli import get_default_data_paths, init_engine
from .decorator import PolicyViolationError, semantic_matcher
from .engine.matcher import SemanticMatcher
from .guard import PolicyGuard, check_prompt, evaluate_prompt
from .models import MatchResult, Policy, PredecomposedPolicy
from .storage.indexer import PolicyIndexer
from .storage.markdown_loader import load_policies_from_markdown
from .storage.oscal_loader import (
    export_to_oscal,
    get_oscal_component_definition,
    is_oscal_catalog,
    load_oscal_catalog,
)

__all__ = [
    "__version__",
    "semantic_matcher",
    "PolicyViolationError",
    "PolicyGuard",
    "check_prompt",
    "evaluate_prompt",
    "SemanticMatcher",
    "init_engine",
    "get_default_data_paths",
    "MatchResult",
    "Policy",
    "PredecomposedPolicy",
    "PolicyIndexer",
    "load_policies_from_markdown",
    "load_oscal_catalog",
    "export_to_oscal",
    "is_oscal_catalog",
    "get_oscal_component_definition",
]

