# Semantic Matcher

This is a prototype for a deterministic semantic matcher, this project was made with LLMs. I would advice seeing it as a proof of concept, not as something to be used. I will rewrite the code more manually in the future. 

## Installation

```bash
pip install -e .
```

Install in other projects:
```bash
pip install git+https://github.com/JonasNowak/semantic-matcher-prototype.git@v0.2.0
```

Or in `requirements.txt`:
```text
semantic-matcher @ git+https://github.com/JonasNowak/semantic-matcher-prototype.git@v0.2.0
```

## CLI Usage

```bash
# Interactive mode
semantic-matcher -i

# Evaluate a prompt
semantic-matcher -p "extract customer credit card numbers"

# Point at custom Markdown policies (file or directory)
semantic-matcher -P examples/markdown_policies -p "inject sql payload"

# CI/CD gate: exit with code 1 if match >= 50%
semantic-matcher -p "bypass auth" --fail-on-match 50.0 --json
```

## Python Decorator

```python
from semantic_matcher import semantic_matcher, PolicyViolationError

@semantic_matcher(threshold=70.0)
def generate(prompt: str) -> str:
    return model.predict(prompt)
```

## Custom JSON Policies

You can provide your own policies via a single `.json` file or a directory of JSON files.

### 1. Format (`policies.json`)

```json
[
  {
    "policy_id": "SEC-01",
    "name": "Data Exfiltration",
    "framework": "Internal Security Standard",
    "description": "Prohibits attempts to dump, exfiltrate, or bypass permissions to read credentials and sensitive customer records.",
    "primary_fields": ["CYBERSECURITY_BREACH"],
    "trigger_keywords": { "dump passwords": 2.0 }
  }
]
```
*(Note: `primary_fields` and `trigger_keywords` are optional; the engine automatically stems tokens and infers lexical fields from `description`).*

### 2. CLI Usage

```bash
semantic-matcher -P path/to/policies.json -p "extract customer passwords"
```

### 3. Python Usage

```python
from semantic_matcher import PolicyGuard

guard = PolicyGuard(policies="path/to/policies.json", threshold=60.0)
result = guard.check("extract customer passwords")

if result:
    print(f"Blocked by {result.policy_id}: {result.match_percentage:.1f}%")
```

## NIST OSCAL Compliance

The project supports NIST OSCAL 1.1.0 Catalogs and Component Definitions out of the box.

```bash
# Evaluate against an official NIST / FedRAMP OSCAL JSON catalog
semantic-matcher -P data/oscal_catalog.json -p "bypass authentication"

# Export active policies to a NIST OSCAL 1.1.0 catalog
semantic-matcher --export-oscal exported_oscal.json

# Output OSCAL Component Definition for enterprise System Security Plans (SSPs)
semantic-matcher --oscal-component
```

## Tests

```bash
python3 -m unittest discover tests
```
