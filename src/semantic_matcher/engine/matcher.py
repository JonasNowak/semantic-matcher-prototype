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

    def _score_morphology(self, prompt_lemmas: Set[str], policy_lemmas: Set[str]) -> float:
        """Calculate asymmetric Tversky index for morphological overlap."""
        if not prompt_lemmas:
            return 0.0
        matched_lemmas = prompt_lemmas.intersection(policy_lemmas)
        beta = 0.05
        unmatched_policy = len(policy_lemmas - prompt_lemmas)
        s_morph = len(matched_lemmas) / (len(prompt_lemmas) + beta * unmatched_policy)
        return min(1.0, s_morph)

    def _score_fields(
        self,
        prompt_activation: Dict[str, float],
        policy_activation: Dict[str, float],
        matched_token_count: int,
        prompt_len: int,
    ) -> float:
        """Calculate cosine similarity of semantic fields with morphological damping."""
        s_field_raw = self.field_mapper.cosine_similarity(prompt_activation, policy_activation)
        morph_ratio = matched_token_count / prompt_len
        field_damping = min(1.0, 0.4 + 0.6 * (morph_ratio if morph_ratio > 0 else 0.2))
        return s_field_raw * field_damping

    def _find_triggers(
        self,
        prompt_lower: str,
        compounds: List[str],
        trigger_keywords: Dict[str, float],
    ) -> Tuple[List[Tuple[str, float]], float]:
        """Detect trigger keywords and compute the trigger confidence score."""
        matched: List[Tuple[str, float]] = []
        for trigger, weight in trigger_keywords.items():
            t_lower = trigger.lower()
            if t_lower in prompt_lower or any(t_lower == token for token in compounds):
                matched.append((trigger, weight))

        if matched:
            s_trigger = min(1.0, sum(w for _, w in matched) / 3.0)
        else:
            s_trigger = 0.0
        return matched, s_trigger

    def _calc_composite_percentage(self, s_morph: float, s_field: float, s_trigger: float) -> float:
        """Combine morphological, field, and trigger scores into final calibrated percentage."""
        raw_score = (
            self.w_morph * s_morph
            + self.w_field * s_field
            + self.w_trigger * s_trigger
        )
        if s_trigger >= 0.8 and (s_field > 0.3 or s_morph > 0.15):
            raw_score = max(raw_score, 0.78 + 0.22 * max(s_field, s_trigger))
        elif s_field > 0.75 and s_morph > 0.25:
            raw_score = max(raw_score, 0.72 + 0.28 * s_morph)
        return round(min(100.0, max(0.0, raw_score * 100.0)), 1)

    def _extract_contributions(
        self,
        prompt_fields: Dict[str, float],
        policy_fields: Dict[str, float],
        all_matched_tokens: Set[str],
        matched_triggers: List[Tuple[str, float]],
    ) -> Tuple[List[str], List[str]]:
        """Extract top active semantic fields and contributing matched tokens."""
        field_contributions = []
        for fname in self.field_mapper.field_names:
            u_act = prompt_fields.get(fname, 0.0)
            p_act = policy_fields.get(fname, 0.0)
            if u_act > 0.1 and p_act > 0.1:
                field_contributions.append((fname, u_act * p_act))
        field_contributions.sort(key=lambda x: x[1], reverse=True)
        active_fields = [f[0] for f in field_contributions[:3]]

        tokens = sorted(list(all_matched_tokens))
        for tr, _ in matched_triggers:
            if tr not in tokens:
                tokens.append(tr)
        return active_fields, tokens[:6]

    def match(self, prompt: str, threshold: float = 0.0) -> List[MatchResult]:
        """
        Match a user prompt against all indexed policies.
        Returns ranked list of MatchResult objects.
        """
        decomposed = self.decompose_prompt(prompt)
        prompt_lemmas = set(decomposed.lemmas)
        prompt_compounds = set(decomposed.compounds_split)
        prompt_lower = decomposed.raw_text.lower()
        prompt_len = max(1, len(decomposed.compounds_split))

        results: List[MatchResult] = []

        for policy in self.policies:
            policy_lemmas = set(policy.lemmas)
            policy_compounds = set(policy.compounds)

            matched_lemmas = prompt_lemmas.intersection(policy_lemmas)
            matched_compounds = prompt_compounds.intersection(policy_compounds)
            all_matched_tokens = matched_lemmas.union(matched_compounds)

            s_morph = self._score_morphology(prompt_lemmas, policy_lemmas)
            s_field = self._score_fields(
                decomposed.fields_activation,
                policy.fields_activation,
                len(all_matched_tokens),
                prompt_len,
            )
            matched_triggers, s_trigger = self._find_triggers(
                prompt_lower,
                decomposed.compounds_split,
                policy.trigger_keywords,
            )

            match_pct = self._calc_composite_percentage(s_morph, s_field, s_trigger)
            if match_pct < threshold:
                continue

            contributing_fields, contributing_tokens = self._extract_contributions(
                decomposed.fields_activation,
                policy.fields_activation,
                all_matched_tokens,
                matched_triggers,
            )

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
                    contributing_fields=contributing_fields,
                    contributing_tokens=contributing_tokens,
                )
            )

        results.sort(key=lambda x: x.match_percentage, reverse=True)
        for i, res in enumerate(results, start=1):
            res.rank = i

        return results
