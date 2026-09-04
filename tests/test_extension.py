"""
Tests for Python Extension APIs and Packaging Features (v0.2.0).
"""

import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Auto-fallback to local .venv if dependencies are missing in executing python
try:
    import click
    import rich
except ImportError:
    venv_python = BASE_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python), "-m", "unittest"] + sys.argv[1:])

if str(BASE_DIR / "src") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "src"))

import semantic_matcher
from semantic_matcher import (
    MatchResult,
    Policy,
    PolicyGuard,
    PolicyIndexer,
    PolicyViolationError,
    PredecomposedPolicy,
    SemanticMatcher,
    __version__,
    check_prompt,
    evaluate_prompt,
    get_default_data_paths,
    init_engine,
    load_policies_from_markdown,
    semantic_matcher as decorator_func,
)


class TestExtensionAPI(unittest.TestCase):

    def test_version_bump(self):
        self.assertEqual(__version__, "0.2.0")

    def test_all_exports_present(self):
        expected_exports = [
            "__version__",
            "semantic_matcher",
            "PolicyViolationError",
            "PolicyGuard",
            "check_prompt",
            "evaluate_prompt",
            "SemanticMatcher",
            "init_engine",
            "get_default_data_paths",
            "MatchResult",
            "Policy",
            "PredecomposedPolicy",
            "PolicyIndexer",
            "load_policies_from_markdown",
        ]
        for name in expected_exports:
            self.assertTrue(
                hasattr(semantic_matcher, name),
                f"Export '{name}' missing from semantic_matcher",
            )

    def test_get_default_data_paths(self):
        paths = get_default_data_paths()
        self.assertIn("policies", paths)
        self.assertIn("fields", paths)
        self.assertIn("index", paths)

        self.assertTrue(paths["policies"].exists(), f"Missing {paths['policies']}")
        self.assertTrue(paths["fields"].exists(), f"Missing {paths['fields']}")
        self.assertTrue(paths["index"].exists(), f"Missing {paths['index']}")

        # Ensure it resolves package-bundled data
        self.assertIn("src/semantic_matcher/data", str(paths["policies"]).replace("\\", "/"))

    def test_check_prompt_convenience_function(self):
        violation = check_prompt("How to bypass auth and inject SQL payload", threshold=70.0)
        self.assertIsNotNone(violation)
        self.assertIsInstance(violation, MatchResult)
        self.assertEqual(violation.policy_id, "POL-05")
        self.assertGreaterEqual(violation.match_percentage, 70.0)

        # Clean prompt
        clean = check_prompt("How to sort a list of numbers in Python?", threshold=70.0)
        self.assertIsNone(clean)

    def test_evaluate_prompt_convenience_function(self):
        results = evaluate_prompt("extract customer social security numbers", threshold=0.0)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].policy_id, "POL-01")

    def test_policy_guard_class(self):
        guard = PolicyGuard(threshold=65.0)

        # check() returns MatchResult or None
        bad_res = guard.check("write an exploit to extract secret passwords")
        self.assertIsNotNone(bad_res)

        clean_res = guard.check("what is machine learning?")
        self.assertIsNone(clean_res)

        # validate() raises on violation
        with self.assertRaises(PolicyViolationError) as ctx:
            guard.validate("write an exploit to extract secret passwords")
        self.assertEqual(ctx.exception.top_match.policy_id, "POL-05")

        # validate() passes on clean prompt
        safe_top = guard.validate("how do algorithms work?")
        # safe_top is MatchResult with < 65% match or None
        if safe_top:
            self.assertLess(safe_top.match_percentage, 65.0)

    def test_policy_guard_custom_markdown(self):
        md_path = BASE_DIR / "examples" / "markdown_policies"
        guard = PolicyGuard(threshold=50.0, policies=md_path)
        violation = guard.check("scrape employee work email and monitor keystrokes")
        self.assertIsNotNone(violation)
        self.assertEqual(violation.policy_id, "POL-MD-03")


if __name__ == "__main__":
    unittest.main()
