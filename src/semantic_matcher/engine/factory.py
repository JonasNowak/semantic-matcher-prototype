"""
Engine factory and configuration.
Locates bundled/repo data paths and initializes the SemanticMatcher engine.
"""

from pathlib import Path
from typing import Dict, Optional

from ..storage.indexer import PolicyIndexer
from .matcher import SemanticMatcher

_DEFAULT_MATCHER: Optional[SemanticMatcher] = None


def get_default_data_paths() -> Dict[str, Path]:
    """Locate default data directory bundled with package or in repo root."""
    # 1. First check package-bundled data directory (works when installed via pip/wheel)
    pkg_data_dir = Path(__file__).resolve().parent.parent / "data"
    if (pkg_data_dir / "policies.json").exists():
        data_dir = pkg_data_dir
    else:
        # 2. Fallback to repository root for local unpackaged development
        repo_data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
        data_dir = repo_data_dir if repo_data_dir.exists() else pkg_data_dir

    return {
        "policies": data_dir / "policies.json",
        "fields": data_dir / "lexical_fields.json",
        "index": data_dir / "policy_index.json",
    }


def init_engine(
    rebuild: bool = False,
    policies_path: Optional[Path] = None,
    fields_path: Optional[Path] = None,
    index_path: Optional[Path] = None,
) -> SemanticMatcher:
    """Initialize and return a SemanticMatcher instance."""
    global _DEFAULT_MATCHER

    is_default = (
        not rebuild
        and policies_path is None
        and fields_path is None
        and index_path is None
    )
    if is_default and _DEFAULT_MATCHER is not None:
        return _DEFAULT_MATCHER

    defaults = get_default_data_paths()
    p_path = Path(policies_path) if policies_path else defaults["policies"]
    f_path = Path(fields_path) if fields_path else defaults["fields"]
    i_path = Path(index_path) if index_path else (defaults["index"] if policies_path is None else None)

    indexer = PolicyIndexer(
        policies_path=p_path,
        fields_path=f_path,
        index_path=i_path,
    )
    policies = indexer.get_or_load_index(force_rebuild=rebuild)

    matcher = SemanticMatcher(
        policies=policies,
        field_mapper=indexer.field_mapper,
        decompounder=indexer.decompounder,
    )

    if is_default:
        _DEFAULT_MATCHER = matcher

    return matcher
