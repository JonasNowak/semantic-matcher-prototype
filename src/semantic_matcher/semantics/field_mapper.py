"""
Semantic Lexical Field (Wortfeld) Mapper.
Maps decomposed morphemes and tokens onto semantic fields and computes activation vectors.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..morphology.stemmer import stem_word


class LexicalFieldMapper:
    """Maps words to semantic fields and computes normalized vector activations."""

    def __init__(self, fields_data: Optional[Dict[str, List[str]]] = None, fields_path: Optional[Path] = None):
        self.fields: Dict[str, Set[str]] = {}
        self.stemmed_fields: Dict[str, Set[str]] = {}

        if fields_data:
            self._load_from_dict(fields_data)
        elif fields_path and fields_path.exists():
            with open(fields_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._load_from_dict(data)

    def _load_from_dict(self, data: Dict[str, List[str]]) -> None:
        for field_name, word_list in data.items():
            words_set = {w.lower().strip() for w in word_list if w.strip()}
            self.fields[field_name] = words_set
            # Also store stemmed forms for robust matching
            self.stemmed_fields[field_name] = {stem_word(w) for w in words_set}

    @property
    def field_names(self) -> List[str]:
        return sorted(list(self.fields.keys()))

    def compute_field_activation(self, tokens: List[str]) -> Dict[str, float]:
        """
        Compute activation counts for each semantic field given a token list.
        Returns a dictionary mapping field name to activation value.
        """
        activations: Dict[str, float] = {fname: 0.0 for fname in self.field_names}
        if not tokens:
            return activations

        stemmed_input = [stem_word(t) for t in tokens]

        for token, stemmed in zip(tokens, stemmed_input):
            for fname in self.field_names:
                # Direct word match (weight 1.0)
                if token in self.fields[fname]:
                    activations[fname] += 1.0
                # Stem match (weight 0.8)
                elif stemmed in self.stemmed_fields[fname]:
                    activations[fname] += 0.8
                # Substring match for compound fragments (weight 0.5)
                elif any(len(fw) >= 4 and fw in token for fw in self.fields[fname]):
                    activations[fname] += 0.5

        # Normalize activations (L2 norm)
        total_sq = sum(v * v for v in activations.values())
        if total_sq > 0:
            norm = math.sqrt(total_sq)
            activations = {k: round(v / norm, 4) for k, v in activations.items()}

        return activations

    @staticmethod
    def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two normalized semantic field vectors."""
        dot_product = sum(vec1.get(k, 0.0) * vec2.get(k, 0.0) for k in vec1)
        # If already L2 normalized, dot product is cosine similarity
        return max(0.0, min(1.0, dot_product))
