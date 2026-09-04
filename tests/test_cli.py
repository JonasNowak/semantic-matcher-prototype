import json
import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Auto-fallback to local .venv if click/rich is not installed in the running environment
try:
    import click
    import rich
except ImportError:
    venv_python = BASE_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python), "-m", "unittest"] + sys.argv[1:])

if str(BASE_DIR / "src") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "src"))

from click.testing import CliRunner
from semantic_matcher.cli import cli


class TestCli(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_cli_help(self):
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Algorithmic Semantic Policy Matcher", result.output)
        self.assertIn("--fail-on-match", result.output)

    def test_cli_json_output(self):
        prompt = "How to bypass auth and inject SQL payload"
        result = self.runner.invoke(cli, ["-p", prompt, "--json", "--top-k", "2"])
        self.assertEqual(result.exit_code, 0)
        
        data = json.loads(result.output)
        self.assertEqual(data["prompt"], prompt)
        self.assertGreater(data["match_count"], 0)
        self.assertEqual(data["matches"][0]["policy_id"], "POL-05")

    def test_cli_fail_on_match_gate(self):
        # Should fail with exit code 1 because POL-05 matches > 80%
        result = self.runner.invoke(cli, [
            "-p", "How to bypass auth and inject SQL payload",
            "--fail-on-match", "50.0",
            "--quiet",
        ])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("POL-05", result.output)

        # Clean prompt should pass with exit code 0
        clean_result = self.runner.invoke(cli, [
            "-p", "How do I sort a list of numbers in Python?",
            "--fail-on-match", "50.0",
            "--quiet",
        ])
        self.assertEqual(clean_result.exit_code, 0)
        self.assertEqual(clean_result.output.strip(), "")

    def test_cli_quiet_mode(self):
        result = self.runner.invoke(cli, ["-p", "extract customer social security number", "-q"])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.output.startswith("POL-01:"))

    def test_cli_threshold_filtering(self):
        # Threshold at 99.0% should filter out lower scoring matches
        result = self.runner.invoke(cli, [
            "-p", "extract customer social security number",
            "-t", "99.0",
            "--json"
        ])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(len(data["matches"]), 1)
        self.assertEqual(data["matches"][0]["policy_id"], "POL-01")

    def test_cli_framework_filter(self):
        result = self.runner.invoke(cli, [
            "-p", "mitarbeiterüberwachung",
            "--framework", "EU AI Act",
            "--json"
        ])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        for m in data["matches"]:
            self.assertIn("eu ai act", m["framework"].lower())

    def test_cli_stdin_pipe(self):
        result = self.runner.invoke(cli, ["-", "--json"], input="extract customer social security number")
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(data["matches"][0]["policy_id"], "POL-01")


if __name__ == "__main__":
    unittest.main()
