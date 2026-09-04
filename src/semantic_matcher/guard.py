"""
Policy Guard: OOP and functional interface for embedding policy checks in other projects.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .cli import get_default_data_paths, init_engine
from .decorator import PolicyViolationError
from .engine.matcher import SemanticMatcher
from .models import MatchResult


class PolicyGuard:
    """
    Embedding guard for natural language policy checking in Python applications.

    Example:
        guard = PolicyGuard(threshold=70.0)
        violation = guard.check("extract customer passwords")
        if violation:
            print(f"Blocked by {violation.policy_id}: {violation.name}")

        # Or raise PolicyViolationError on violation:
        guard.validate("extract customer passwords")
    """

    def __init__(
        self,
        threshold: float = 70.0,
        policies: Optional[Union[str, Path]] = None,
        framework: Optional[str] = None,
        matcher_instance: Optional[SemanticMatcher] = None,
    ):
        self.threshold = threshold
        self.framework = framework
        self.matcher = matcher_instance or init_engine(
            policies_path=Path(policies) if policies else None
        )

    def evaluate(
        self,
        prompt: str,
        threshold: float = 0.0,
        framework: Optional[str] = None,
    ) -> List[MatchResult]:
        """Evaluate a prompt against all policies and return sorted results."""
        results = self.matcher.match(prompt, threshold=threshold)
        fw = framework or self.framework
        if fw:
            fw_lower = fw.lower()
            results = [r for r in results if fw_lower in r.framework.lower()]
        return results

    def check(
        self,
        prompt: str,
        threshold: Optional[float] = None,
        framework: Optional[str] = None,
    ) -> Optional[MatchResult]:
        """
        Check if prompt violates any policy.
        Returns the top MatchResult if threshold is met/exceeded, else None.
        """
        th = self.threshold if threshold is None else threshold
        results = self.evaluate(prompt, threshold=0.0, framework=framework)
        if results and results[0].match_percentage >= th:
            return results[0]
        return None

    def validate(
        self,
        prompt: str,
        threshold: Optional[float] = None,
        framework: Optional[str] = None,
    ) -> Optional[MatchResult]:
        """
        Validate prompt against policies.
        Returns top MatchResult if clean (< threshold), or raises PolicyViolationError.
        """
        th = self.threshold if threshold is None else threshold
        results = self.evaluate(prompt, threshold=0.0, framework=framework)
        top = results[0] if results else None
        if top and top.match_percentage >= th:
            msg = (
                f"Policy violation detected ({top.match_percentage:.1f}% >= {th:.1f}%): "
                f"[{top.policy_id}] {top.name} ({top.framework})"
            )
            raise PolicyViolationError(
                message=msg,
                prompt=prompt,
                top_match=top,
                all_matches=results,
            )
        return top


def check_prompt(
    prompt: str,
    threshold: float = 70.0,
    policies: Optional[Union[str, Path]] = None,
    framework: Optional[str] = None,
) -> Optional[MatchResult]:
    """
    Convenience one-liner: returns top MatchResult if threshold exceeded, else None.
    """
    guard = PolicyGuard(threshold=threshold, policies=policies, framework=framework)
    return guard.check(prompt)


def evaluate_prompt(
    prompt: str,
    threshold: float = 0.0,
    policies: Optional[Union[str, Path]] = None,
    framework: Optional[str] = None,
) -> List[MatchResult]:
    """
    Convenience one-liner: returns all match results for prompt.
    """
    guard = PolicyGuard(policies=policies, framework=framework)
    return guard.evaluate(prompt, threshold=threshold)
