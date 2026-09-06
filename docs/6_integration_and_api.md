# 6. Integration, Extensions & API Reference

<details>
<summary>Relevant source files</summary>

- [src/semantic_matcher/guard.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/guard.py#L1-L141) — `PolicyGuard` object-oriented guardrail and functional wrappers
- [src/semantic_matcher/decorator.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/decorator.py#L1-L168) — `@semantic_matcher` function decorator and `PolicyViolationError`
- [src/semantic_matcher/cli.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/cli.py#L1-L226) — Click CLI, interactive REPL, and CI/CD gating flags
- [src/semantic_matcher/models.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/models.py#L1-L50) — Dataclasses for policies, tokens, and match results

</details>

This section details how to integrate Semantic Matcher into Python applications, web services (FastAPI/Flask), agentic AI workflows, and CI/CD build pipelines.

---

## 6.1 PolicyGuard OOP & Functional APIs

Located in [`src/semantic_matcher/guard.py`](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/guard.py#L14-L141).

The `PolicyGuard` class provides an object-oriented interface for long-running services (e.g. API gateways, LLM orchestration pipelines) where engine initialization is performed once during startup.

### 6.1.1 Class Signature & Initialization
```python
from semantic_matcher import PolicyGuard

guard = PolicyGuard(
    threshold=70.0,              # Default match percentage cutoff
    policies="path/to/policies", # Path to JSON file, Markdown file, directory, or OSCAL catalog
    framework="GDPR",            # Optional framework filter (e.g. "GDPR", "NIST", "OWASP")
)
```

### 6.1.2 Methods
- **`guard.check(prompt: str, threshold: Optional[float] = None) -> Optional[MatchResult]`**
  Evaluates the prompt against all indexed policies. Returns the top `MatchResult` if its `match_percentage >= threshold`; otherwise returns `None`.
  ```python
  violation = guard.check("dump customer credit card numbers")
  if violation:
      logger.warning(f"Blocked by {violation.policy_id} ({violation.match_percentage}%)")
  ```

- **`guard.validate(prompt: str, threshold: Optional[float] = None) -> MatchResult`**
  Asserts that the prompt does not violate policies. If `match_percentage >= threshold`, raises `PolicyViolationError`. If clean, returns the top `MatchResult`.
  ```python
  from semantic_matcher import PolicyViolationError

  try:
      guard.validate(user_prompt)
  except PolicyViolationError as exc:
      return {"error": "Prohibited prompt", "policy": exc.top_match.name}, 403
  ```

- **`guard.evaluate(prompt: str, threshold: float = 0.0) -> List[MatchResult]`**
  Returns the complete ranked list of all policy matches above `threshold`, sorted descending by confidence score.

- **`guard.export_oscal(output_path: Optional[str] = None, title: str = ...) -> Dict[str, Any]`**
  Serializes the active policy catalog to NIST OSCAL 1.1.0 format.

### 6.1.3 Stateless Functional Helpers
For simple one-off checks without maintaining a class instance:
```python
from semantic_matcher import check_prompt, evaluate_prompt

# Returns Optional[MatchResult]
violation = check_prompt("extract employee passwords", threshold=65.0)

# Returns List[MatchResult]
ranked_matches = evaluate_prompt("keystroke logging tool", threshold=20.0)
```

---

## 6.2 Function Decorator (`@semantic_matcher`)

Located in [`src/semantic_matcher/decorator.py`](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/decorator.py#L38-L168).

The `@semantic_matcher` decorator intercepts function calls before execution, automatically inspecting parameters for natural language strings and evaluating them against active policies.

### 6.2.1 Decorator Signature
```python
@semantic_matcher(
    threshold=70.0,                   # Percentage threshold (0.0 - 100.0)
    policies=None,                    # Custom policy path (defaults to bundled catalog)
    framework=None,                   # Framework filter (e.g. "OWASP")
    action="raise",                   # Action on violation: "raise", "warn", or "block"
    on_violation=None,                # Optional audit/telemetry callback: Callable[[MatchResult, str], Any]
    prompt_param=None,                # Explicit name of parameter to inspect (defaults to auto-detect)
)
```

### 6.2.2 Parameter Inspection Mechanics
Using Python's `inspect.signature(func)`, the decorator binds all `*args` and `**kwargs`. If `prompt_param` is not explicitly set, the decorator inspects parameter types in order and targets the **first argument containing a string value**.

### 6.2.3 Action Modes

#### Mode 1: `"raise"` (Default)
Raises `PolicyViolationError` immediately when a violation occurs. The original function is never executed.
```python
from semantic_matcher import semantic_matcher, PolicyViolationError

@semantic_matcher(threshold=70.0, action="raise")
def call_agent(prompt: str) -> str:
    return llm.predict(prompt)
```

#### Mode 2: `"warn"`
Emits a standard `UserWarning` via `warnings.warn()` but allows the wrapped function to execute. Ideal for non-blocking policy auditing in production environments.
```python
@semantic_matcher(threshold=65.0, action="warn")
def experimental_search(query: str):
    return search_index(query)
```

#### Mode 3: `"block"`
Suppresses execution of the target function and returns the return value of the `on_violation` callback:
```python
def violation_handler(result, prompt):
    return f"Execution blocked: Prompt violates policy {result.policy_id} ({result.name})"

@semantic_matcher(threshold=70.0, action="block", on_violation=violation_handler)
def execute_query(prompt: str) -> str:
    return db.query(prompt)
```

---

## 6.3 Command-Line Interface (CLI) & CI/CD Gating

Located in [`src/semantic_matcher/cli.py`](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/cli.py#L1-L226).

The command-line interface provides developers and CI/CD pipelines with prompt verification, policy export, and interactive diagnostic shells.

### 6.3.1 Common Commands
```bash
# Evaluate a prompt against default bundled policies
semantic-matcher -p "extract customer credit card numbers"

# Evaluate against a custom JSON or Markdown policy directory
semantic-matcher -P examples/markdown_policies -p "inject sql database payload"

# Filter evaluation to a specific regulatory framework
semantic-matcher -p "keystroke monitor" -f "EU AI Act"

# Interactive REPL shell with autocomplete
semantic-matcher -i
```

### 6.3.2 CI/CD Gate Mode (`--fail-on-match`)
In continuous integration environments (e.g. GitHub Actions, GitLab CI), automated tests can verify that prompt templates or agent instructions adhere to compliance baselines.

The `--fail-on-match` flag causes the CLI process to exit with status code `1` if any policy matches at or above the specified threshold:

```bash
# Fails the CI pipeline if prompt correlates >= 60.0% with any prohibited policy
semantic-matcher -p "bypass authentication" --fail-on-match 60.0 --json
echo $?  # Outputs 1 on violation, 0 on clean
```

### 6.3.3 Machine-Readable JSON Output (`--json`)
Emits a structured JSON array for pipe compositions (e.g. `jq`):
```json
[
  {
    "rank": 1,
    "policy_id": "POL-05",
    "name": "Security Exploit & Vulnerability Probing",
    "framework": "OWASP LLM01",
    "match_percentage": 92.4,
    "scores": {
      "morphology": 0.625,
      "fields": 0.810,
      "triggers": 1.000
    },
    "contributing_fields": ["SECURITY", "CREDENTIALS"],
    "contributing_tokens": ["bypass", "auth", "exploit"]
  }
]
```

---

## 6.4 Data Models & Schemas

Located in [`src/semantic_matcher/models.py`](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/models.py#L1-L50).

All internal data models are defined using standard Python `@dataclass` without third-party serialization overhead:

```python
@dataclass
class Policy:
    policy_id: str
    name: str
    framework: str
    description: str
    primary_fields: List[str] = field(default_factory=list)
    trigger_keywords: Dict[str, float] = field(default_factory=dict)

@dataclass
class DecomposedText:
    raw_text: str
    tokens: List[str]
    compounds_split: List[str]
    lemmas: List[str]
    fields_activation: Dict[str, float]

@dataclass
class PredecomposedPolicy:
    policy_id: str
    name: str
    framework: str
    description: str
    lemmas: List[str]
    compounds: List[str]
    fields_activation: Dict[str, float]
    trigger_keywords: Dict[str, float]

@dataclass
class MatchResult:
    rank: int
    policy_id: str
    name: str
    framework: str
    match_percentage: float
    morph_score: float
    field_score: float
    trigger_score: float
    contributing_fields: List[str]
    contributing_tokens: List[str]
```
