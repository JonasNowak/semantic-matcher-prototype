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

## Tests

```bash
python3 -m unittest discover tests
```
