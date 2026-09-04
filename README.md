# Semantic Matcher (v0.2.0)

> **Deterministic algorithmic semantic & morphological policy matcher for natural language prompts and LLM guardrails.**
> 
> *Note: This prototype was built as a deterministic proof of concept for governance matching without runtime LLM calls. It is designed to be embedded directly into other Python projects as an extension or dependency.*

---

## Packaging & Installation in Other Projects

Because this project is currently not published to the public PyPI index (due to pending review of AI usage policies), it is fully packaged to be installable directly via standard Python package managers (`pip`, `uv`, `poetry`, etc.) using Git URLs, local paths, or pre-built wheels.

### 1. Install via Git (Pip)

Install directly from GitHub into any virtual environment or container:

```bash
# Latest main branch
pip install git+https://github.com/JonasNowak/semantic-matcher-prototype.git

# Or pinned to v0.2.0 release tag
pip install git+https://github.com/JonasNowak/semantic-matcher-prototype.git@v0.2.0
```

### 2. In `requirements.txt` of another project

Add the following entry to your project's `requirements.txt`:

```text
semantic-matcher @ git+https://github.com/JonasNowak/semantic-matcher-prototype.git@v0.2.0
```

### 3. In `pyproject.toml` of another project

#### PEP 621 / Standard `pip` / `uv`:
```toml
[project]
dependencies = [
    "semantic-matcher @ git+https://github.com/JonasNowak/semantic-matcher-prototype.git@v0.2.0",
]
```

Using `uv`:
```bash
uv add "semantic-matcher @ git+https://github.com/JonasNowak/semantic-matcher-prototype.git@v0.2.0"
```

#### Poetry:
```bash
poetry add git+https://github.com/JonasNowak/semantic-matcher-prototype.git#v0.2.0
```
Or in `pyproject.toml`:
```toml
[tool.poetry.dependencies]
semantic-matcher = { git = "https://github.com/JonasNowak/semantic-matcher-prototype.git", tag = "v0.2.0" }
```

### 4. Local Editable / Monorepo Development

If developing across multiple local repositories or a monorepo:

```bash
pip install -e /path/to/semantic-matcher-prototype
```

### 5. Pre-Built Wheel (`.whl`) Distribution

Build a standalone wheel (includes all default policies and data bundled):

```bash
python -m build
# Produces: dist/semantic_matcher-0.2.0-py3-none-any.whl
```

Install the wheel in any other project or container without internet access or git:

```bash
pip install dist/semantic_matcher-0.2.0-py3-none-any.whl
```

---

## Using as a Python Extension in Other Projects

Once installed, `semantic_matcher` exposes clean, zero-overhead interfaces for embedding into LLM applications, API services, ETL pipelines, and agent loops.

### Option A: Reusable Guard Object (`PolicyGuard`)

Ideal for stateful agents, FastAPI/Flask request handlers, or LangChain / LlamaIndex guardrails:

```python
from semantic_matcher import PolicyGuard, PolicyViolationError

# Initialize guard (bundles zero-latency cached index)
guard = PolicyGuard(threshold=70.0)

# Non-throwing inspection (returns MatchResult or None)
violation = guard.check("extract customer social security numbers")
if violation:
    print(f"Blocked by {violation.policy_id} ({violation.match_percentage:.1f}% match)")

# Enforcing mode: raises PolicyViolationError if threshold exceeded
try:
    guard.validate("write an exploit to inject SQL and bypass auth")
except PolicyViolationError as exc:
    print(f"Rejected: [{exc.top_match.policy_id}] {exc.top_match.name}")
```

### Option B: Quick Functional Check (`check_prompt` & `evaluate_prompt`)

For lightweight one-liner evaluations:

```python
from semantic_matcher import check_prompt, evaluate_prompt

# Returns top MatchResult if match >= threshold, otherwise None
violation = check_prompt("dump secret AWS access credentials", threshold=65.0)
if violation:
    raise ValueError(f"Input violates policy: {violation.name}")

# Get all ranked matches for analysis
all_matches = evaluate_prompt("scrape employee emails", threshold=0.0)
for match in all_matches[:3]:
    print(f"{match.rank}. [{match.policy_id}] {match.name}: {match.match_percentage:.1f}%")
```

### Option C: Python Function Decorator (`@semantic_matcher`)

Automatically guard LLM generation functions or tool handlers:

```python
from semantic_matcher import semantic_matcher, PolicyViolationError

# Intercepts prompt parameter before function runs
@semantic_matcher(threshold=70.0, action="raise")
def ask_assistant(prompt: str) -> str:
    return model.generate(prompt)

# Or warn instead of raising:
@semantic_matcher(threshold=60.0, action="warn")
def process_query(prompt: str) -> str:
    return run_query(prompt)
```

### Option D: Custom Markdown Policies

Load company-specific governance rules directly from Markdown files:

```python
from semantic_matcher import PolicyGuard

# Point to a Markdown file or a folder of .md policies
guard = PolicyGuard(
    threshold=60.0,
    policies="path/to/custom_markdown_policies/"
)

violation = guard.check("scrape employee work email and track webcam")
```

### Option E: Direct Core Engine (`SemanticMatcher`)

For maximum control over policies, lexical fields, and decompounder dictionaries:

```python
from semantic_matcher import init_engine

engine = init_engine(rebuild=False)
results = engine.match("bypass login authentication", threshold=0.0)
for r in results:
    print(f"{r.policy_id}: {r.match_percentage:.1f}%")
```

---

## CLI Usage

The package installs the `semantic-matcher` console script:

```bash
# Interactive evaluation mode
semantic-matcher -i

# Single prompt check
semantic-matcher -p "extract customer credit card numbers"

# Filter by compliance framework
semantic-matcher -p "user personal data" --framework GDPR

# Point to custom Markdown policies
semantic-matcher -P examples/markdown_policies -p "monitor employee keystrokes"

# CI/CD Gate: Exit with status code 1 if match >= 60%
semantic-matcher -p "bypass auth" --fail-on-match 60.0 --json
```

---

## Running Tests

```bash
python3 -m unittest discover tests
```
