"""
Storage and Pre-decomposition Indexer for Policies.
Decomposes policies offline once and caches them to disk to ensure zero-latency runtime lookups.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..models import Policy, PredecomposedPolicy
from ..morphology.decompounder import Decompounder
from ..morphology.stemmer import stem_tokens
from ..morphology.tokenizer import tokenize
from ..semantics.field_mapper import LexicalFieldMapper


class PolicyIndexer:
    """Pre-decomposes and caches policy catalog."""

    def __init__(
        self,
        policies_path: Path,
        fields_path: Path,
        index_path: Optional[Path] = None,
    ):
        self.policies_path = Path(policies_path)
        self.fields_path = Path(fields_path)

        if index_path is not None:
            self.index_path = Path(index_path)
        else:
            if self.policies_path.is_dir():
                self.index_path = self.policies_path / ".policy_index.json"
            elif self.policies_path.suffix.lower() in [".md", ".markdown"]:
                self.index_path = self.policies_path.with_suffix(".index.json")
            else:
                self.index_path = self.policies_path.parent / "policy_index.json"

        self.field_mapper = LexicalFieldMapper(fields_path=fields_path)
        self.decompounder = Decompounder()

        # Augment decompounder with words from lexical fields
        for field_words in self.field_mapper.fields.values():
            self.decompounder.add_words(list(field_words))

    def load_raw_policies(self) -> List[Policy]:
        """Load raw policies from JSON or Markdown (file or directory)."""
        if self.policies_path.is_dir():
            # Check for JSON files in directory (ignoring cached index files)
            json_files = sorted([
                f for f in self.policies_path.glob("*.json")
                if not f.name.endswith("index.json") and not f.name.startswith(".")
            ])
            if json_files:
                policies: List[Policy] = []
                for jf in json_files:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            policies.extend([Policy(**item) for item in data])
                        elif isinstance(data, dict):
                            policies.append(Policy(**data))
                if policies:
                    return policies

            from .markdown_loader import load_policies_from_markdown
            return load_policies_from_markdown(self.policies_path)

        if self.policies_path.suffix.lower() in [".md", ".markdown"]:
            from .markdown_loader import load_policies_from_markdown
            return load_policies_from_markdown(self.policies_path)

        with open(self.policies_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [Policy(**item) for item in data]
        elif isinstance(data, dict):
            return [Policy(**data)]
        return []

    def decompose_policy(self, policy: Policy) -> PredecomposedPolicy:
        """Decompose a single policy into morphemes and semantic activations."""
        # Combine text sources for complete coverage
        full_text = f"{policy.name} {policy.description} {' '.join(policy.primary_fields)} {' '.join(policy.trigger_keywords.keys())}"
        
        # Tokenize
        raw_tokens = tokenize(full_text)
        
        # Decompound West-Germanic words
        compounds_split = self.decompounder.decompose_tokens(raw_tokens)
        
        # Stem all morphemes
        stemmed_tokens = stem_tokens(compounds_split)
        unique_lemmas = sorted(list(set(stemmed_tokens)))
        
        # Calculate semantic field activations
        fields_activation = self.field_mapper.compute_field_activation(compounds_split)
        
        # Explicit boost for designated primary fields if defined
        for pf in policy.primary_fields:
            if pf in fields_activation:
                fields_activation[pf] = max(fields_activation[pf], 0.70)

        # Re-normalize field activation vector (L2 norm)
        import math
        norm = math.sqrt(sum(v * v for v in fields_activation.values()))
        if norm > 0:
            fields_activation = {k: round(v / norm, 4) for k, v in fields_activation.items()}

        return PredecomposedPolicy(
            policy_id=policy.policy_id,
            name=policy.name,
            framework=policy.framework,
            description=policy.description,
            lemmas=unique_lemmas,
            compounds=sorted(list(set(compounds_split))),
            fields_activation=fields_activation,
            trigger_keywords=policy.trigger_keywords,
        )

    def build_and_save_index(self) -> List[PredecomposedPolicy]:
        """Build pre-decomposed index and write to disk."""
        raw_policies = self.load_raw_policies()
        decomposed: List[PredecomposedPolicy] = []

        for p in raw_policies:
            decomposed.append(self.decompose_policy(p))

        # Save to JSON cache if directory is writable
        try:
            index_data = [
                {
                    "policy_id": dp.policy_id,
                    "name": dp.name,
                    "framework": dp.framework,
                    "description": dp.description,
                    "lemmas": dp.lemmas,
                    "compounds": dp.compounds,
                    "fields_activation": dp.fields_activation,
                    "trigger_keywords": dp.trigger_keywords,
                }
                for dp in decomposed
            ]

            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

        return decomposed

    def get_or_load_index(self, force_rebuild: bool = False) -> List[PredecomposedPolicy]:
        """Load pre-decomposed index, building it if missing or requested or if source is newer."""
        if force_rebuild or not self.index_path.exists():
            return self.build_and_save_index()

        # Check if source policy file or directory has been modified after cache was written
        try:
            cache_mtime = self.index_path.stat().st_mtime
            if self.policies_path.is_file() and self.policies_path.stat().st_mtime > cache_mtime:
                return self.build_and_save_index()
            elif self.policies_path.is_dir():
                dir_mtime = max(
                    (f.stat().st_mtime for f in self.policies_path.glob("**/*") if not f.name.startswith(".")),
                    default=0.0,
                )
                if dir_mtime > cache_mtime:
                    return self.build_and_save_index()
        except OSError:
            pass

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return [
                PredecomposedPolicy(
                    policy_id=item["policy_id"],
                    name=item["name"],
                    framework=item["framework"],
                    description=item["description"],
                    lemmas=item["lemmas"],
                    compounds=item["compounds"],
                    fields_activation=item["fields_activation"],
                    trigger_keywords=item["trigger_keywords"],
                )
                for item in data
            ]
        except Exception:
            return self.build_and_save_index()
