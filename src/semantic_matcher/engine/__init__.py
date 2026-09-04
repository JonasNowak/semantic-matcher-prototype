"""Engine package for semantic matching."""

from .factory import get_default_data_paths, init_engine
from .matcher import SemanticMatcher

__all__ = ["SemanticMatcher", "init_engine", "get_default_data_paths"]

