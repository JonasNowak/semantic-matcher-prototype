"""
Semantic Policy Matcher
Algorithmic semantic & morphological policy matcher for natural language prompts.
"""

__version__ = "0.1.0"

from .decorator import PolicyViolationError, semantic_matcher

__all__ = ["semantic_matcher", "PolicyViolationError", "__version__"]
