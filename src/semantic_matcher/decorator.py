"""
Python Decorator for Semantic Policy Matcher.

Allows protecting Python functions, LLM agents, and prompt handlers
directly with policy validation without shelling out to `python3 main.py`.
"""

import functools
import inspect
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .cli import init_engine
from .engine.matcher import SemanticMatcher
from .models import MatchResult


class PolicyViolationError(ValueError):
    """Raised when an input prompt violates an active governance policy."""

    def __init__(
        self,
        message: str,
        prompt: str,
        top_match: MatchResult,
        all_matches: List[MatchResult],
    ):
        super().__init__(message)
        self.prompt = prompt
        self.top_match = top_match
        self.all_matches = all_matches

    def __repr__(self) -> str:
        return f"<PolicyViolationError: {self.top_match.policy_id} ({self.top_match.match_percentage:.1f}%)>"


def _make_decorator(
    threshold: float = 70.0,
    policies: Optional[Union[str, Path]] = None,
    framework: Optional[str] = None,
    action: str = "raise",
    on_violation: Optional[Callable[[MatchResult, str], Any]] = None,
    prompt_param: Optional[str] = None,
    matcher_instance: Optional[SemanticMatcher] = None,
) -> Callable:
    """Internal builder for the policy checking decorator."""

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        # Lazily initialize matcher instance
        engine = matcher_instance or init_engine(
            rebuild=False,
            policies_path=Path(policies) if policies else None,
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Identify target prompt string
            prompt_val: Optional[str] = None
            if prompt_param and prompt_param in bound_args.arguments:
                val = bound_args.arguments[prompt_param]
                if isinstance(val, str):
                    prompt_val = val
            else:
                # Find the first string argument
                for val in bound_args.arguments.values():
                    if isinstance(val, str):
                        prompt_val = val
                        break

            if prompt_val:
                results = engine.match(prompt_val, threshold=0.0)
                if framework:
                    fw_lower = framework.lower()
                    results = [r for r in results if fw_lower in r.framework.lower()]

                top = results[0] if results else None
                wrapper.last_matches = results
                wrapper.last_top_match = top

                if top and top.match_percentage >= threshold:
                    msg = (
                        f"Policy violation detected ({top.match_percentage:.1f}% >= {threshold:.1f}%): "
                        f"[{top.policy_id}] {top.name} ({top.framework})"
                    )

                    if on_violation:
                        callback_res = on_violation(top, prompt_val)
                        if action == "block":
                            return callback_res

                    if action == "raise":
                        raise PolicyViolationError(
                            message=msg,
                            prompt=prompt_val,
                            top_match=top,
                            all_matches=results,
                        )
                    elif action == "warn":
                        warnings.warn(msg, UserWarning, stacklevel=2)
                    elif action == "block":
                        return None

            return func(*args, **kwargs)

        wrapper.matcher = engine
        wrapper.last_matches = []
        wrapper.last_top_match = None
        return wrapper

    return decorator


def semantic_matcher(
    func: Optional[Callable] = None,
    *,
    threshold: float = 70.0,
    policies: Optional[Union[str, Path]] = None,
    framework: Optional[str] = None,
    action: str = "raise",
    on_violation: Optional[Callable[[MatchResult, str], Any]] = None,
    prompt_param: Optional[str] = None,
    matcher_instance: Optional[SemanticMatcher] = None,
) -> Callable:
    """
    Decorator that checks prompts against policies before function execution.

    Can be used with or without arguments:
        @semantic_matcher
        def ask(prompt: str): ...

        @semantic_matcher(threshold=60.0, policies="examples/markdown_policies")
        def ask(prompt: str): ...

    Args:
        threshold: Minimum match percentage (0.0 - 100.0) to consider a violation.
        policies: Optional path to Markdown file/dir or JSON catalog.
        framework: Optional framework filter string.
        action: 'raise' (raises PolicyViolationError), 'warn' (UserWarning), or 'block' (returns None or on_violation result).
        on_violation: Optional callback (top_match, prompt) -> Any.
        prompt_param: Parameter name to inspect. Defaults to first str argument.
        matcher_instance: Optional pre-built SemanticMatcher instance.
    """
    if func is not None and callable(func):
        return _make_decorator(
            threshold=threshold,
            policies=policies,
            framework=framework,
            action=action,
            on_violation=on_violation,
            prompt_param=prompt_param,
            matcher_instance=matcher_instance,
        )(func)

    return _make_decorator(
        threshold=threshold,
        policies=policies,
        framework=framework,
        action=action,
        on_violation=on_violation,
        prompt_param=prompt_param,
        matcher_instance=matcher_instance,
    )
