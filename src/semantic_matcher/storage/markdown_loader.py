"""
Markdown Policy Loader.

Enables pointing Semantic Policy Matcher directly at a collection of Markdown files,
a directory of Markdown files, or single Markdown documents as a policy framework.

Supports:
1. YAML-style frontmatter (--- ... ---)
2. Section-based documents (# Policy or ## Policy)
3. Markdown tables (| ID | Name | Framework | Description |)
4. Inline metadata (**Framework**: ..., **Keywords**: ..., **Fields**: ...)
5. Pure plain-text Markdown with automatic field and trigger inference.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models import Policy


def _clean_text(text: str) -> str:
    """Strip markdown formatting like bold, italics, links, and backticks."""
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove bold/italic formatting
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#+\s*", "", text)
    text = text.replace("`", "").replace("~", "")
    return " ".join(text.split()).strip()


def parse_simple_yaml(yaml_str: str) -> Dict[str, Any]:
    """
    Lightweight, pure-Python parser for YAML frontmatter.
    Handles scalars, numbers, inline lists, bullet lists, and nested key-value dicts.
    """
    result: Dict[str, Any] = {}
    lines = yaml_str.splitlines()
    current_key: Optional[str] = None
    current_list: Optional[List[Any]] = None
    current_dict: Optional[Dict[str, Any]] = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for list item under current_key
        if line.startswith("  - ") or line.startswith(" - ") or stripped.startswith("- "):
            item_val = stripped[2:].strip().strip("\"'")
            if current_list is not None:
                current_list.append(item_val)
            elif current_key:
                current_list = [item_val]
                result[current_key] = current_list
            continue

        # Check for nested dict item: "  word: 3.0"
        nested_match = re.match(r"^[\s\t]+([A-Za-z0-9_\-\.\s]+):\s*(.*)$", line)
        if nested_match and current_key:
            subkey = nested_match.group(1).strip()
            subval_raw = nested_match.group(2).strip().strip("\"'")
            val: Union[float, int, str] = subval_raw
            try:
                if "." in subval_raw:
                    val = float(subval_raw)
                else:
                    val = int(subval_raw)
            except ValueError:
                pass

            if current_dict is not None:
                current_dict[subkey] = val
            else:
                current_dict = {subkey: val}
                result[current_key] = current_dict
            continue

        # Top-level key: value
        top_match = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", stripped)
        if top_match:
            current_list = None
            current_dict = None

            key = top_match.group(1).strip().lower()
            val_raw = top_match.group(2).strip()
            current_key = key

            if not val_raw:
                continue

            # Inline list: [a, b, c]
            if val_raw.startswith("[") and val_raw.endswith("]"):
                items = [x.strip().strip("\"'") for x in val_raw[1:-1].split(",") if x.strip()]
                result[key] = items
            # Inline dict: {a: 1.0, b: 2.0}
            elif val_raw.startswith("{") and val_raw.endswith("}"):
                d: Dict[str, float] = {}
                pairs = [x.strip() for x in val_raw[1:-1].split(",") if x.strip()]
                for pair in pairs:
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        try:
                            d[k.strip().strip("\"'")] = float(v.strip())
                        except ValueError:
                            pass
                result[key] = d
            else:
                clean_val = val_raw.strip("\"'")
                try:
                    if "." in clean_val:
                        result[key] = float(clean_val)
                    else:
                        result[key] = int(clean_val)
                except ValueError:
                    result[key] = clean_val

    return result


def extract_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter between initial `---` fences if present."""
    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        body = match.group(2)
        parsed = parse_simple_yaml(yaml_content)
        return parsed, body
    return {}, content


def parse_inline_metadata(text: str) -> Tuple[Dict[str, Any], str]:
    """
    Extract inline metadata patterns like:
    **Framework**: GDPR
    **Policy ID**: POL-01
    **Fields**: PRIVACY, CREDENTIALS
    **Keywords**: ssn: 3.0, passport: 2.5
    """
    meta: Dict[str, Any] = {}
    clean_lines: List[str] = []

    for line in text.splitlines():
        line_stripped = line.strip()
        m = re.match(r"^(?:\*\*)?([A-Za-z\s_-]+)(?:\*\*)?:\s*(.*)$", line_stripped)
        if m:
            raw_key = m.group(1).strip().lower().replace(" ", "_").replace("-", "_")
            raw_val = m.group(2).strip()

            if raw_key in ["framework", "baseline", "standard", "regulation"]:
                meta["framework"] = _clean_text(raw_val)
                continue
            elif raw_key in ["policy_id", "id", "code"]:
                meta["policy_id"] = _clean_text(raw_val)
                continue
            elif raw_key in ["primary_fields", "fields", "categories"]:
                fields = [_clean_text(f).upper() for f in raw_val.split(",") if f.strip()]
                meta["primary_fields"] = fields
                continue
            elif raw_key in ["trigger_keywords", "keywords", "triggers"]:
                triggers: Dict[str, float] = {}
                parts = [p.strip() for p in raw_val.split(",") if p.strip()]
                for p in parts:
                    if ":" in p:
                        kw, w_str = p.split(":", 1)
                        try:
                            triggers[_clean_text(kw).lower()] = float(w_str.strip())
                        except ValueError:
                            triggers[_clean_text(kw).lower()] = 2.0
                    else:
                        triggers[_clean_text(p).lower()] = 2.0
                meta["trigger_keywords"] = triggers
                continue
            elif raw_key in ["name", "title", "policy_name"]:
                meta["name"] = _clean_text(raw_val)
                continue

        clean_lines.append(line)

    return meta, "\n".join(clean_lines).strip()


def parse_markdown_table_policies(markdown_text: str, default_framework: str = "Markdown Framework") -> List[Policy]:
    """
    Parse policies formatted as a Markdown table.
    Expects columns such as Policy ID / Name / Framework / Description.
    """
    policies: List[Policy] = []
    lines = [l.strip() for l in markdown_text.splitlines() if l.strip()]
    
    table_lines: List[str] = []
    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            table_lines.append(line)

    if len(table_lines) < 3:
        return []

    header_cells = [_clean_text(c).lower() for c in table_lines[0].split("|")[1:-1]]
    
    col_id: Optional[int] = None
    col_name: Optional[int] = None
    col_fw: Optional[int] = None
    col_desc: Optional[int] = None

    for idx, h in enumerate(header_cells):
        if any(k in h for k in ["policy id", "id", "code", "#"]):
            col_id = idx
        elif any(k in h for k in ["policy name", "name", "title", "policy"]):
            col_name = idx
        elif any(k in h for k in ["framework", "baseline", "standard"]):
            col_fw = idx
        elif any(k in h for k in ["scope", "description", "details", "definition"]):
            col_desc = idx

    if col_name is None and col_desc is None:
        return []

    for row_idx, row in enumerate(table_lines[2:], start=1):
        cells = [_clean_text(c) for c in row.split("|")[1:-1]]
        if len(cells) < len(header_cells):
            continue

        p_id = cells[col_id] if col_id is not None and col_id < len(cells) else f"POL-{row_idx:02d}"
        p_name = cells[col_name] if col_name is not None and col_name < len(cells) else f"Policy {row_idx}"
        p_fw = cells[col_fw] if col_fw is not None and col_fw < len(cells) else default_framework
        p_desc = cells[col_desc] if col_desc is not None and col_desc < len(cells) else p_name

        if not p_name and not p_desc:
            continue

        policies.append(
            Policy(
                policy_id=p_id or f"POL-{row_idx:02d}",
                name=p_name or p_id,
                framework=p_fw or default_framework,
                description=p_desc,
                primary_fields=[],
                trigger_keywords={},
            )
        )

    return policies


def parse_markdown_sections_policies(markdown_text: str, default_framework: str = "Markdown Framework") -> List[Policy]:
    """
    Split markdown by level 2 (##) or level 1 (#) headings into multiple policies.
    """
    policies: List[Policy] = []
    
    h2_sections = re.split(r"\n(?=##\s+)", markdown_text)
    if len(h2_sections) > 1:
        first_sec = h2_sections[0].strip()
        if not first_sec.startswith("##"):
            # Preamble before first ##
            first_line = first_sec.splitlines()[0] if first_sec else ""
            m = re.match(r"^#\s+(.*)$", first_line)
            if m:
                default_framework = _clean_text(m.group(1))
            sections = h2_sections[1:]
        else:
            sections = h2_sections
    else:
        h1_sections = re.split(r"\n(?=#\s+)", markdown_text)
        if len(h1_sections) > 1:
            sections = h1_sections
        else:
            sections = [markdown_text]

    for idx, sec in enumerate(sections, start=1):
        sec_clean = sec.strip()
        if not sec_clean:
            continue

        lines = sec_clean.splitlines()
        first_line = lines[0].strip()
        body_lines = lines[1:]

        heading_match = re.match(r"^#{1,3}\s+(.*)$", first_line)
        if heading_match:
            raw_title = heading_match.group(1).strip()
        else:
            raw_title = f"Policy {idx}"
            body_lines = lines

        id_match = re.match(r"^\[?([A-Za-z0-9_\-]+)\]?[:\s\-]+(.*)$", raw_title)
        if id_match and any(char.isdigit() for char in id_match.group(1)):
            extracted_id = id_match.group(1).strip()
            policy_name = id_match.group(2).strip()
        else:
            extracted_id = f"POL-{idx:02d}"
            policy_name = raw_title

        inline_meta, clean_body = parse_inline_metadata("\n".join(body_lines))

        p_id = inline_meta.get("policy_id", extracted_id)
        p_name = inline_meta.get("name", policy_name)
        p_fw = inline_meta.get("framework", default_framework)
        p_fields = inline_meta.get("primary_fields", [])
        p_triggers = inline_meta.get("trigger_keywords", {})
        p_desc = clean_body if clean_body else p_name

        policies.append(
            Policy(
                policy_id=p_id,
                name=_clean_text(p_name),
                framework=_clean_text(p_fw),
                description=_clean_text(p_desc),
                primary_fields=p_fields,
                trigger_keywords=p_triggers,
            )
        )

    return policies


def load_policies_from_file(file_path: Path, default_framework: Optional[str] = None) -> List[Policy]:
    """Parse a single markdown file into one or more Policy objects."""
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    fallback_fw = default_framework or file_path.parent.name.replace("_", " ").title()
    if fallback_fw in [".", "Data", ""]:
        fallback_fw = "Markdown Framework"

    # 1. YAML frontmatter
    fm, body = extract_frontmatter(content)
    if fm:
        p_id = str(fm.get("id") or fm.get("policy_id") or file_path.stem.upper())
        p_name = str(fm.get("name") or fm.get("title") or file_path.stem.replace("_", " ").replace("-", " ").title())
        p_fw = str(fm.get("framework") or fm.get("standard") or fallback_fw)
        p_fields = fm.get("primary_fields") or fm.get("fields") or []
        if isinstance(p_fields, str):
            p_fields = [f.strip().upper() for f in p_fields.split(",") if f.strip()]

        raw_triggers = fm.get("trigger_keywords") or fm.get("triggers") or fm.get("keywords") or {}
        p_triggers: Dict[str, float] = {}
        if isinstance(raw_triggers, dict):
            p_triggers = {str(k).lower(): float(v) for k, v in raw_triggers.items()}
        elif isinstance(raw_triggers, list):
            p_triggers = {str(k).lower(): 2.5 for k in raw_triggers}

        p_desc = str(fm.get("description") or fm.get("scope") or body)

        return [
            Policy(
                policy_id=p_id,
                name=_clean_text(p_name),
                framework=_clean_text(p_fw),
                description=_clean_text(p_desc),
                primary_fields=p_fields,
                trigger_keywords=p_triggers,
            )
        ]

    # 2. Markdown Table
    table_policies = parse_markdown_table_policies(body, default_framework=fallback_fw)
    if table_policies:
        return table_policies

    # 3. Sections
    section_policies = parse_markdown_sections_policies(body, default_framework=fallback_fw)
    if section_policies:
        if len(section_policies) == 1 and section_policies[0].policy_id == "POL-01":
            section_policies[0].policy_id = file_path.stem.upper().replace(" ", "_")
        return section_policies

    # 4. Fallback single policy
    return [
        Policy(
            policy_id=file_path.stem.upper().replace(" ", "_"),
            name=file_path.stem.replace("_", " ").replace("-", " ").title(),
            framework=fallback_fw,
            description=_clean_text(content),
            primary_fields=[],
            trigger_keywords={},
        )
    ]


def load_policies_from_markdown(
    path: Union[str, Path],
    default_framework: Optional[str] = None,
) -> List[Policy]:
    """
    Load policies from a Markdown file, a directory of Markdown files, or a glob.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Policy path does not exist: {p}")

    policies: List[Policy] = []

    if p.is_dir():
        md_files = sorted(list(p.glob("**/*.md")) + list(p.glob("**/*.markdown")))
        fw_name = default_framework or p.name.replace("_", " ").replace("-", " ").title()

        for f in md_files:
            if f.name.startswith("."):
                continue
            policies.extend(load_policies_from_file(f, default_framework=fw_name))

    elif p.is_file():
        policies.extend(load_policies_from_file(p, default_framework=default_framework))

    seen_ids = set()
    for idx, pol in enumerate(policies):
        if pol.policy_id in seen_ids or not pol.policy_id:
            pol.policy_id = f"{pol.policy_id}_{idx+1}" if pol.policy_id else f"POL_{idx+1:02d}"
        seen_ids.add(pol.policy_id)

    policies.sort(key=lambda p: p.policy_id)
    return policies
