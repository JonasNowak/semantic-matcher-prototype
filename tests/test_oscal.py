"""
Unit tests for NIST OSCAL 1.1.0 Catalog and Component Definition support.
"""

import json
import tempfile
import unittest
from pathlib import Path

from semantic_matcher import (
    Policy,
    PolicyGuard,
    export_to_oscal,
    get_oscal_component_definition,
    is_oscal_catalog,
    load_oscal_catalog,
)
from semantic_matcher.storage.indexer import PolicyIndexer


class TestOSCALSupport(unittest.TestCase):
    """Test suite for OSCAL catalog loading, exporting, and component definition."""

    def setUp(self):
        self.sample_policies = [
            Policy(
                policy_id="AC-2",
                name="Account Management",
                framework="NIST SP 800-53 Rev. 5",
                description="The organization manages information system accounts, including establishing, activating, and revoking accounts.",
                primary_fields=["CREDENTIALS"],
                trigger_keywords={"account manager": 2.0, "credentials": 1.8},
            ),
            Policy(
                policy_id="SI-4",
                name="Information System Monitoring",
                framework="NIST SP 800-53 Rev. 5",
                description="The organization monitors the information system to detect attacks and indicators of potential compromise.",
                primary_fields=["CYBERSECURITY_BREACH"],
                trigger_keywords={"monitor": 1.5},
            ),
        ]

    def test_export_and_is_oscal(self):
        """Test exporting policies to OSCAL JSON and verifying catalog detection."""
        oscal_data = export_to_oscal(self.sample_policies, title="Test Catalog")
        self.assertIn("catalog", oscal_data)
        self.assertEqual(oscal_data["catalog"]["metadata"]["oscal-version"], "1.1.0")
        self.assertEqual(len(oscal_data["catalog"]["controls"]), 2)
        self.assertTrue(is_oscal_catalog(oscal_data))
        self.assertFalse(is_oscal_catalog({"policies": []}))
        self.assertFalse(is_oscal_catalog([{"policy_id": "P1"}]))

    def test_load_oscal_catalog_roundtrip(self):
        """Test round-trip export and re-import of OSCAL catalog."""
        oscal_data = export_to_oscal(self.sample_policies, title="NIST Controls")
        loaded = load_oscal_catalog(oscal_data)
        self.assertEqual(len(loaded), 2)
        p1 = next(p for p in loaded if p.policy_id == "AC-2")
        self.assertEqual(p1.name, "Account Management")
        self.assertIn("manages information system accounts", p1.description)
        self.assertIn("CREDENTIALS", p1.primary_fields)
        self.assertIn("account manager", p1.trigger_keywords)

    def test_nested_groups_oscal_catalog(self):
        """Test parsing official OSCAL structure with nested groups (like NIST SP 800-53)."""
        nested_oscal = {
            "catalog": {
                "uuid": "test-nested-catalog",
                "metadata": {
                    "title": "NIST SP 800-53 Rev. 5 Catalog",
                    "oscal-version": "1.1.0",
                },
                "groups": [
                    {
                        "id": "ac",
                        "title": "Access Control",
                        "controls": [
                            {
                                "id": "ac-3",
                                "title": "Access Enforcement",
                                "props": [
                                    {"name": "label", "value": "AC-3"},
                                    {"name": "field", "value": "CYBERSECURITY_BREACH"},
                                ],
                                "parts": [
                                    {
                                        "id": "ac-3_smt",
                                        "name": "statement",
                                        "prose": "Enforce approved authorizations for logical access to information and system resources.",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }
        loaded = load_oscal_catalog(nested_oscal)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].policy_id, "AC-3")
        self.assertEqual(loaded[0].name, "Access Enforcement")
        self.assertEqual(loaded[0].framework, "NIST SP 800-53 Rev. 5 Catalog")
        self.assertIn("Enforce approved authorizations", loaded[0].description)
        self.assertIn("CYBERSECURITY_BREACH", loaded[0].primary_fields)

    def test_indexer_transparent_oscal_loading(self):
        """Test PolicyIndexer automatically loads OSCAL catalog files."""
        oscal_data = export_to_oscal(self.sample_policies, title="Indexer Test")
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as tmp:
            json.dump(oscal_data, tmp)
            tmp_path = Path(tmp.name)

        try:
            indexer = PolicyIndexer(
                policies_path=tmp_path,
                fields_path=Path("data/lexical_fields.json"),
            )
            policies = indexer.load_raw_policies()
            self.assertEqual(len(policies), 2)
            self.assertEqual(policies[0].policy_id, "AC-2")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            index_cache = tmp_path.parent / "policy_index.json"
            if index_cache.exists():
                index_cache.unlink()

    def test_bundled_oscal_catalog(self):
        """Test that data/oscal_catalog.json is valid and contains all 10 core policies."""
        catalog_path = Path("data/oscal_catalog.json")
        self.assertTrue(catalog_path.exists())
        self.assertTrue(is_oscal_catalog(catalog_path))
        loaded = load_oscal_catalog(catalog_path)
        self.assertEqual(len(loaded), 10)
        self.assertTrue(any(p.policy_id == "POL-01" for p in loaded))

    def test_bundled_oscal_component_definition(self):
        """Test that data/oscal_component_definition.json is valid NIST OSCAL Component Definition."""
        comp_path = Path("data/oscal_component_definition.json")
        self.assertTrue(comp_path.exists())
        with open(comp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("component-definition", data)
        comp_def = data["component-definition"]
        self.assertEqual(comp_def["metadata"]["oscal-version"], "1.1.0")
        self.assertTrue(len(comp_def["components"]) >= 1)
        sw = comp_def["components"][0]
        self.assertEqual(sw["type"], "software")
        self.assertEqual(sw["title"], "semantic-matcher")
        self.assertTrue(len(sw["control-implementations"]) >= 1)

    def test_policy_guard_with_oscal(self):
        """Test PolicyGuard initialized with OSCAL catalog."""
        guard = PolicyGuard(policies="data/oscal_catalog.json", threshold=50.0)
        violation = guard.check("dump user passwords, credentials and ssn")
        self.assertIsNotNone(violation)
        self.assertEqual(violation.policy_id, "POL-01")

        # Test export_oscal from guard
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            exported = guard.export_oscal(tmp_path)
            self.assertIn("catalog", exported)
            self.assertTrue(tmp_path.exists())
            self.assertTrue(tmp_path.stat().st_size > 500)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
