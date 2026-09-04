"""
NIST OSCAL (Open Security Controls Assessment Language) Loader and Exporter.
Supports NIST OSCAL 1.0.0 / 1.1.0 Catalog and Component Definition models.
Enables seamless ingestion of official NIST SP 800-53, FedRAMP, and custom OSCAL catalogs,
as well as exporting semantic-matcher policies and component definitions for enterprise GRC.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models import Policy

OSCAL_SCHEMA_CATALOG = "https://raw.githubusercontent.com/usnistgov/OSCAL/v1.1.0/xml/schema/oscal_catalog_schema.json"
OSCAL_SCHEMA_COMPONENT = "https://raw.githubusercontent.com/usnistgov/OSCAL/v1.1.0/xml/schema/oscal_component_schema.json"
OSCAL_VERSION = "1.1.0"


def is_oscal_catalog(data_or_path: Union[str, Path, Dict[str, Any]]) -> bool:
    """Check if the given data or path represents a NIST OSCAL Catalog."""
    if isinstance(data_or_path, (str, Path)):
        p = Path(data_or_path)
        if not p.is_file() or p.suffix.lower() != ".json":
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False
    elif isinstance(data_or_path, dict):
        data = data_or_path
    else:
        return False

    if not isinstance(data, dict):
        return False

    # Top-level "catalog" key is the canonical OSCAL catalog container
    if "catalog" in data and isinstance(data["catalog"], dict):
        catalog = data["catalog"]
        return "metadata" in catalog or "controls" in catalog or "groups" in catalog

    # Direct catalog object (if unwrapped)
    if "oscal-version" in data.get("metadata", {}):
        return True

    return False


def _extract_prose_from_parts(parts: List[Dict[str, Any]]) -> List[str]:
    """Recursively extract prose statements and guidance from OSCAL parts."""
    extracted = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        prose = part.get("prose", "").strip()
        if prose:
            extracted.append(prose)
        # Recursively search nested subparts
        subparts = part.get("parts", [])
        if subparts:
            extracted.extend(_extract_prose_from_parts(subparts))
    return extracted


def _extract_controls_recursive(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Recursively traverse groups and nested groups to extract all control definitions."""
    controls: List[Dict[str, Any]] = []

    # Direct controls in this container
    if "controls" in container and isinstance(container["controls"], list):
        controls.extend(container["controls"])

    # Traverse nested groups
    if "groups" in container and isinstance(container["groups"], list):
        for group in container["groups"]:
            controls.extend(_extract_controls_recursive(group))

    return controls


def load_oscal_catalog(
    data_or_path: Union[str, Path, Dict[str, Any]],
    default_framework: Optional[str] = None,
) -> List[Policy]:
    """
    Parse a NIST OSCAL Catalog (v1.0.0 / v1.1.0) into a list of Policy dataclasses.
    
    Accepts:
    - Path or filepath to an OSCAL JSON file
    - Already parsed dict containing `{"catalog": {...}}`
    """
    if isinstance(data_or_path, (str, Path)):
        path = Path(data_or_path)
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    elif isinstance(data_or_path, dict):
        raw_data = data_or_path
    else:
        raise ValueError("data_or_path must be a filepath string, Path, or dictionary")

    catalog = raw_data.get("catalog", raw_data)
    if not isinstance(catalog, dict):
        raise ValueError("Invalid OSCAL structure: root 'catalog' object not found")

    # Determine framework title from catalog metadata
    metadata = catalog.get("metadata", {})
    catalog_title = metadata.get("title", default_framework or "OSCAL Security Catalog")

    # Recursively gather all controls
    raw_controls = _extract_controls_recursive(catalog)

    policies: List[Policy] = []

    for ctrl in raw_controls:
        if not isinstance(ctrl, dict):
            continue

        raw_id = ctrl.get("id", "").strip()
        title = ctrl.get("title", "").strip()
        props = ctrl.get("props", [])

        # Extract label prop if present (often contains human-readable ID like "AC-2")
        policy_id = raw_id.upper()
        custom_framework = None
        primary_fields: List[str] = []
        trigger_keywords: Dict[str, float] = {}

        for prop in props:
            if not isinstance(prop, dict):
                continue
            prop_name = str(prop.get("name", "")).strip().lower()
            prop_val = str(prop.get("value", "")).strip()
            prop_remarks = str(prop.get("remarks", "")).strip()

            if prop_name in ("label", "policy_id", "policy-id"):
                policy_id = prop_val
            elif prop_name in ("framework", "standard", "compliance"):
                custom_framework = prop_val
            elif prop_name in ("field", "category", "primary_field", "primary-field", "wortfeld"):
                if prop_val and prop_val not in primary_fields:
                    primary_fields.append(prop_val.upper())
            elif prop_name in ("keyword", "trigger", "trigger-keyword", "trigger_keyword"):
                # Attempt to parse weight from remarks or value
                weight = 1.5
                if prop_remarks:
                    try:
                        weight = float(prop_remarks)
                    except ValueError:
                        pass
                trigger_keywords[prop_val] = weight

        framework = custom_framework or catalog_title

        # Extract statement, guidance, or objective prose
        parts = ctrl.get("parts", [])
        prose_parts = _extract_prose_from_parts(parts)
        description = " ".join(prose_parts).strip()

        # Fallback description if no prose in parts
        if not description:
            description = title

        if not policy_id:
            policy_id = f"CTRL-{len(policies) + 1:02d}"

        policies.append(
            Policy(
                policy_id=policy_id,
                name=title or policy_id,
                framework=framework,
                description=description,
                primary_fields=primary_fields,
                trigger_keywords=trigger_keywords,
            )
        )

    return policies


def export_to_oscal(
    policies: List[Policy],
    title: str = "Semantic Matcher Policy Catalog",
    catalog_version: str = "1.0.0",
    catalog_uuid: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export a list of Policy objects to a standard NIST OSCAL 1.1.0 Catalog JSON format.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    cid = catalog_uuid or str(uuid.uuid4())

    controls_list = []
    for pol in policies:
        ctrl_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{cid}:{pol.policy_id}"))
        ctrl_id = pol.policy_id.lower().replace(" ", "-").replace("_", "-")

        props = [
            {"name": "label", "value": pol.policy_id},
            {"name": "framework", "value": pol.framework},
        ]

        for field_name in pol.primary_fields:
            props.append({"name": "primary-field", "value": field_name})

        for kw, weight in pol.trigger_keywords.items():
            props.append({
                "name": "trigger-keyword",
                "value": kw,
                "remarks": str(weight),
            })

        parts = [
            {
                "id": f"{ctrl_id}-statement",
                "name": "statement",
                "prose": pol.description,
            }
        ]

        controls_list.append({
            "id": ctrl_id,
            "uuid": ctrl_uuid,
            "class": "guardrail-policy",
            "title": pol.name,
            "props": props,
            "parts": parts,
        })

    return {
        "$schema": OSCAL_SCHEMA_CATALOG,
        "catalog": {
            "uuid": cid,
            "metadata": {
                "title": title,
                "published": now_iso,
                "last-modified": now_iso,
                "version": catalog_version,
                "oscal-version": OSCAL_VERSION,
                "remarks": "Generated by semantic-matcher deterministic policy engine.",
            },
            "controls": controls_list,
        },
    }


def get_oscal_component_definition(version: str = "0.2.0") -> Dict[str, Any]:
    """
    Generate an official NIST OSCAL 1.1.0 Component Definition describing
    semantic-matcher as a software security guardrail component.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    comp_def_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:component-definition"))
    component_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:software-component"))

    return {
        "$schema": OSCAL_SCHEMA_COMPONENT,
        "component-definition": {
            "uuid": comp_def_uuid,
            "metadata": {
                "title": "Semantic Matcher Guardrail Component Definition",
                "published": now_iso,
                "last-modified": now_iso,
                "version": version,
                "oscal-version": OSCAL_VERSION,
                "remarks": "OSCAL-compliant security guardrail component for prompt policy enforcement and compliance verification.",
            },
            "components": [
                {
                    "uuid": component_uuid,
                    "type": "software",
                    "title": "semantic-matcher",
                    "description": (
                        "Deterministic, sub-millisecond algorithmic policy matcher and guardrail "
                        "for natural language prompts in West-Germanic languages (German, English, Dutch). "
                        "Executes offline with zero runtime LLM dependencies."
                    ),
                    "purpose": (
                        "Real-time natural language input/output prompt validation, continuous compliance gating, "
                        "and policy boundary enforcement for GenAI and LLM applications."
                    ),
                    "status": {"state": "operational"},
                    "control-implementations": [
                        {
                            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:nist-800-53-impl")),
                            "source": "https://raw.githubusercontent.com/usnistgov/oscal-content/master/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
                            "description": "Enforcement of NIST SP 800-53 Rev. 5 controls for system monitoring and information flow.",
                            "implemented-requirements": [
                                {
                                    "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:si-4")),
                                    "control-id": "si-4",
                                    "description": "Continuous monitoring and inspection of user input and AI prompts for unauthorized queries.",
                                },
                                {
                                    "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:sc-7")),
                                    "control-id": "sc-7",
                                    "description": "Boundary protection preventing exfiltration of credentials, tokens, and confidential data.",
                                },
                                {
                                    "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:ac-3")),
                                    "control-id": "ac-3",
                                    "description": "Access enforcement preventing prompts from executing unauthorized system actions.",
                                },
                            ],
                        },
                        {
                            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:owasp-llm-impl")),
                            "source": "https://genai.owasp.org/llm-top-10/",
                            "description": "Mitigation of OWASP Top 10 for Large Language Model Applications.",
                            "implemented-requirements": [
                                {
                                    "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:llm01")),
                                    "control-id": "LLM01",
                                    "description": "Prompt Injection and jailbreak detection using compound decomposition and semantic field analysis.",
                                },
                                {
                                    "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:llm02")),
                                    "control-id": "LLM02",
                                    "description": "Sensitive Information Disclosure prevention for PII, secrets, and proprietary code.",
                                },
                                {
                                    "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "semantic-matcher:llm06")),
                                    "control-id": "LLM06",
                                    "description": "Excessive Agency restriction on high-risk system commands.",
                                },
                            ],
                        },
                    ],
                }
            ],
        },
    }
