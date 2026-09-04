"""Data models for policy matching."""

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Policy:
    policy_id: str
    name: str
    framework: str
    description: str
    primary_fields: List[str] = field(default_factory=list)
    trigger_keywords: Dict[str, float] = field(default_factory=dict)


@dataclass
class DecomposedText:
    raw_text: str
    tokens: List[str]
    compounds_split: List[str]
    lemmas: List[str]
    fields_activation: Dict[str, float]


@dataclass
class PredecomposedPolicy:
    policy_id: str
    name: str
    framework: str
    description: str
    lemmas: List[str]
    compounds: List[str]
    fields_activation: Dict[str, float]
    trigger_keywords: Dict[str, float]


@dataclass
class MatchResult:
    rank: int
    policy_id: str
    name: str
    framework: str
    match_percentage: float
    morph_score: float
    field_score: float
    trigger_score: float
    contributing_fields: List[str]
    contributing_tokens: List[str]
