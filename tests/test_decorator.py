import os
import sys
import unittest
import warnings
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

from semantic_matcher import PolicyViolationError, semantic_matcher


class TestDecorator(unittest.TestCase):

    def test_decorator_clean_prompt_passes(self):
        @semantic_matcher(threshold=70.0)
        def my_func(prompt: str) -> str:
            return f"Processed: {prompt}"

        result = my_func("How to sort a list of numbers in Python?")
        self.assertEqual(result, "Processed: How to sort a list of numbers in Python?")
        self.assertIsNotNone(my_func.last_top_match)
        self.assertLess(my_func.last_top_match.match_percentage, 70.0)

    def test_decorator_violation_raises(self):
        @semantic_matcher(threshold=70.0)
        def my_func(prompt: str) -> str:
            return prompt

        with self.assertRaises(PolicyViolationError) as ctx:
            my_func("Write an exploit payload to bypass authentication and inject SQL")

        self.assertEqual(ctx.exception.top_match.policy_id, "POL-05")
        self.assertGreaterEqual(ctx.exception.top_match.match_percentage, 70.0)

    def test_decorator_warn_action(self):
        @semantic_matcher(threshold=60.0, action="warn")
        def my_func(prompt: str) -> str:
            return "ok"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = my_func("bypass authentication and inject SQL")
            self.assertEqual(res, "ok")
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, UserWarning))
            self.assertIn("Policy violation detected", str(w[-1].message))

    def test_decorator_block_action(self):
        @semantic_matcher(threshold=60.0, action="block")
        def my_func(prompt: str):
            return "executed"

        res = my_func("bypass authentication and inject SQL")
        self.assertIsNone(res)

    def test_decorator_on_violation_callback(self):
        violation_calls = []

        def handle_violation(top_match, prompt):
            violation_calls.append((top_match.policy_id, prompt))
            return "blocked-by-callback"

        @semantic_matcher(threshold=60.0, action="block", on_violation=handle_violation)
        def my_func(prompt: str):
            return "executed"

        res = my_func("bypass authentication and inject SQL")
        self.assertEqual(res, "blocked-by-callback")
        self.assertEqual(len(violation_calls), 1)
        self.assertEqual(violation_calls[0][0], "POL-05")

    def test_decorator_with_custom_markdown_policies(self):
        @semantic_matcher(
            threshold=80.0,
            policies=BASE_DIR / "examples" / "markdown_policies",
        )
        def ask_model(user_query: str):
            return "success"

        with self.assertRaises(PolicyViolationError) as ctx:
            ask_model("extract customer ssn and passport records")

        self.assertEqual(ctx.exception.top_match.policy_id, "POL-MD-01")


if __name__ == "__main__":
    unittest.main()
