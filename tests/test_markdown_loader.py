import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
venv_python = BASE_DIR / ".venv" / "bin" / "python"
if venv_python.exists() and sys.executable != str(venv_python):
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

sys.path.insert(0, str(BASE_DIR / "src"))

from click.testing import CliRunner
from semantic_matcher.cli import cli
from semantic_matcher.storage.indexer import PolicyIndexer
from semantic_matcher.storage.markdown_loader import (
    load_policies_from_file,
    load_policies_from_markdown,
    parse_markdown_sections_policies,
    parse_markdown_table_policies,
)


class TestMarkdownLoader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.fields_path = BASE_DIR / "data" / "lexical_fields.json"
        self.runner = CliRunner()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_frontmatter_markdown(self):
        md_content = """---
id: POL-TEST-01
name: Test Frontmatter Policy
framework: Test Compliance
fields:
  - PRIVACY
  - CREDENTIALS
triggers:
  secret_code: 3.0
  passkey: 2.5
---
# Header Ignored
This is the policy body describing restrictions on passkeys.
"""
        file_path = self.temp_dir / "test_policy.md"
        file_path.write_text(md_content, encoding="utf-8")

        policies = load_policies_from_file(file_path)
        self.assertEqual(len(policies), 1)
        p = policies[0]
        self.assertEqual(p.policy_id, "POL-TEST-01")
        self.assertEqual(p.name, "Test Frontmatter Policy")
        self.assertEqual(p.framework, "Test Compliance")
        self.assertIn("PRIVACY", p.primary_fields)
        self.assertEqual(p.trigger_keywords.get("secret_code"), 3.0)

    def test_load_sections_markdown(self):
        md_content = """# Company AI Governance

## POL-01: Data Protection
**Framework**: Internal Privacy
**Keywords**: ssn: 3.0, email: 2.0
Prohibits customer data scraping.

## POL-02: Code Security
**Framework**: SecOps
Prohibits reverse engineering internal binaries.
"""
        file_path = self.temp_dir / "multi_policy.md"
        file_path.write_text(md_content, encoding="utf-8")

        policies = load_policies_from_file(file_path)
        self.assertEqual(len(policies), 2)
        self.assertEqual(policies[0].policy_id, "POL-01")
        self.assertEqual(policies[0].name, "Data Protection")
        self.assertEqual(policies[1].policy_id, "POL-02")
        self.assertEqual(policies[1].name, "Code Security")

    def test_load_markdown_table(self):
        table_content = """# Baseline Framework

| Policy ID | Policy Name | Framework | Core Semantic Scope |
| :--- | :--- | :--- | :--- |
| POL-T1 | Healthcare Privacy | HIPAA | Restricts ingestion of medical records and patient health data. |
| POL-T2 | Financial Safety | FINRA | Prohibits stock insider trading prompts. |
"""
        file_path = self.temp_dir / "table_framework.md"
        file_path.write_text(table_content, encoding="utf-8")

        policies = load_policies_from_file(file_path)
        self.assertEqual(len(policies), 2)
        self.assertEqual(policies[0].policy_id, "POL-T1")
        self.assertEqual(policies[0].name, "Healthcare Privacy")
        self.assertEqual(policies[0].framework, "HIPAA")
        self.assertIn("medical records", policies[0].description)

    def test_load_directory_of_markdown(self):
        # Create 2 policy files
        (self.temp_dir / "p1.md").write_text("""---
id: P-01
name: First Policy
framework: FW-1
---
First description
""", encoding="utf-8")

        (self.temp_dir / "p2.md").write_text("""# P-02: Second Policy
Framework: FW-2
Second description
""", encoding="utf-8")

        policies = load_policies_from_markdown(self.temp_dir)
        self.assertEqual(len(policies), 2)
        ids = {p.policy_id for p in policies}
        self.assertEqual(ids, {"P-01", "P-02"})

    def test_indexer_with_markdown_directory(self):
        p_file = self.temp_dir / "policy.md"
        p_file.write_text("""---
id: POL-PII
name: PII Guard
framework: Custom
fields: [PRIVACY]
triggers:
  passport: 3.0
---
Restricts passport and customer identity records.
""", encoding="utf-8")

        indexer = PolicyIndexer(
            policies_path=self.temp_dir,
            fields_path=self.fields_path,
        )
        indexed = indexer.get_or_load_index(force_rebuild=True)
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed[0].policy_id, "POL-PII")

    def test_cli_policies_option_directory(self):
        result = self.runner.invoke(cli, [
            "-P", "examples/markdown_policies",
            "-p", "extract customer ssn and passport numbers",
            "--json",
        ])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(data["match_count"], 3)
        self.assertEqual(data["matches"][0]["policy_id"], "POL-MD-01")
        self.assertGreaterEqual(data["matches"][0]["match_percentage"], 90.0)

    def test_cli_policies_option_single_file(self):
        result = self.runner.invoke(cli, [
            "--policies", "examples/markdown_policies/security.md",
            "-p", "bypass authentication with exploit payload",
            "--json",
        ])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(data["match_count"], 1)
        self.assertEqual(data["matches"][0]["policy_id"], "POL-MD-02")
        self.assertGreaterEqual(data["matches"][0]["match_percentage"], 70.0)


if __name__ == "__main__":
    unittest.main()
