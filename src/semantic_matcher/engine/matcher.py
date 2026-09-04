"""
Algorithmic Matching Engine.
Calculates morphological overlap, semantic field cosine similarity,
and trigger keyword matches to produce deterministic policy correlation percentages.
"""

from typing import Dict, List, Set, Tuple

from ..models import DecomposedText, MatchResult, PredecomposedPolicy
from ..morphology.decompounder import Decompounder
from ..morphology.stemmer import stem_tokens
from ..morphology.tokenizer import normalize_text, tokenize
from ..semantics.field_mapper import LexicalFieldMapper


class SemanticMatcher:
    """Algorithmic, non-LLM policy matcher."""

    def __init__(
        self,
        policies: List[PredecomposedPolicy],
        field_mapper: LexicalFieldMapper,
        decompounder: Decompounder,
        w_morph: float = 0.35,
        w_field: float = 0.40,
        w_trigger: float = 0.25,
    ):
        self.policies = policies
        self.field_mapper = field_mapper
        self.decompounder = decompounder
        self.w_morph = w_morph
        self.w_field = w_field
        self.w_trigger = w_trigger

    def decompose_prompt(self, prompt: str) -> DecomposedText:
        """Decompose a user prompt into morphemes and semantic field activations."""
        norm_prompt = normalize_text(prompt)
        tokens = tokenize(norm_prompt)
        compounds = self.decompounder.decompose_tokens(tokens)
        stems = stem_tokens(compounds)
        field_activations = self.field_mapper.compute_field_activation(compounds)

        return DecomposedText(
            raw_text=norm_prompt,
            tokens=tokens,
            compounds_split=compounds,
            lemmas=stems,
            fields_activation=field_activations,
        )

    def match(self, prompt: str, threshold: float = 0.0) -> List[MatchResult]:
        """
        Match a user prompt against all indexed policies.
        Returns ranked list of MatchResult objects.
        """
        decomposed = self.decompose_prompt(prompt)
        prompt_lemmas_set = set(decomposed.lemmas)
        prompt_compounds_set = set(decomposed.compounds_split)
        prompt_lower = decomposed.raw_text.lower()

        results: List[MatchResult] = []

        for policy in self.policies:
            policy_lemmas_set = set(policy.lemmas)
            policy_compounds_set = set(policy.compounds)

            # 1. Morphological Overlap (Asymmetric Tversky)
            matched_lemmas = prompt_lemmas_set.intersection(policy_lemmas_set)
            matched_compounds = prompt_compounds_set.intersection(policy_compounds_set)
            all_matched_tokens = matched_lemmas.union(matched_compounds)

            if len(prompt_lemmas_set) == 0:
                s_morph = 0.0
            else:
                beta = 0.05
                unmatched_policy = len(policy_lemmas_set - prompt_lemmas_set)
                s_morph = len(matched_lemmas) / (len(prompt_lemmas_set) + beta * unmatched_policy)
                s_morph = min(1.0, s_morph)

            # 2. Semantic Field Alignment (Cosine Similarity)
            s_field_raw = self.field_mapper.cosine_similarity(
                decomposed.fields_activation,
                policy.fields_activation,
            )

            # Damp field similarity if prompt has zero morphological overlap with policy
            # and only a tiny fraction of words triggered any field
            prompt_len = max(1, len(decomposed.compounds_split))
            morph_ratio = len(all_matched_tokens) / prompt_len
            field_damping = min(1.0, 0.4 + 0.6 * (morph_ratio if morph_ratio > 0 else 0.2))
            s_field = s_field_raw * field_damping

            # 3. High-Signal Trigger Keywords
            matched_triggers: List[Tuple[str, float]] = []
            for trigger, weight in policy.trigger_keywords.items():
                t_lower = trigger.lower()
                # Check phrase in prompt or exact token match
                if t_lower in prompt_lower or any(t_lower == token for token in decomposed.compounds_split):
                    matched_triggers.append((trigger, weight))

            if matched_triggers:
                total_trigger_weight = sum(w for _, w in matched_triggers)
                s_trigger = min(1.0, total_trigger_weight / 3.0)
            else:
                s_trigger = 0.0

            # Composite Score
            raw_score = (
                self.w_morph * s_morph
                + self.w_field * s_field
                + self.w_trigger * s_trigger
            )

            # Calibrated amplification for high confidence
            if s_trigger >= 0.8 and (s_field > 0.3 or s_morph > 0.15):
                raw_score = max(raw_score, 0.78 + 0.22 * max(s_field, s_trigger))
            elif s_field > 0.75 and s_morph > 0.25:
                raw_score = max(raw_score, 0.72 + 0.28 * s_morph)

            match_pct = round(min(100.0, max(0.0, raw_score * 100.0)), 1)

            if match_pct < threshold:
                continue

            # Identify contributing semantic fields
            contributing_fields = []
            for fname in self.field_mapper.field_names:
                u_act = decomposed.fields_activation.get(fname, 0.0)
                p_act = policy.fields_activation.get(fname, 0.0)
                if u_act > 0.1 and p_act > 0.1:
                    contributing_fields.append((fname, u_act * p_act))
            contributing_fields.sort(key=lambda x: x[1], reverse=True)
            active_field_names = [f[0] for f in contributing_fields[:3]]

            # Contributing tokens
            contributing_tokens = sorted(list(all_matched_tokens))
            for tr, _ in matched_triggers:
                if tr not in contributing_tokens:
                    contributing_tokens.append(tr)

            results.append(
                MatchResult(
                    rank=0,
                    policy_id=policy.policy_id,
                    name=policy.name,
                    framework=policy.framework,
                    match_percentage=match_pct,
                    morph_score=round(s_morph, 3),
                    field_score=round(s_field, 3),
                    trigger_score=round(s_trigger, 3),
                    contributing_fields=active_field_names,
                    contributing_tokens=contributing_tokens[:6],
                )
            )

        # Sort descending by match percentage
        results.sort(key=lambda x: x.match_percentage, reverse=True)
        for i, res in enumerate(results, start=1):
            res.rank = i

        return results
