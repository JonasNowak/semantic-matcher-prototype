# Project Context & Agent Guidelines: Semantic Matcher

This document serves as the project initialization and operational guide (`GEMINI.md` / `/init`) for the **Semantic Matcher** repository.

---

## 1. Project Overview

* **Name**: `semantic-matcher` (v0.2.0)
* **Description**: Deterministic, algorithmic policy matcher and guardrail for natural language prompts in West-Germanic languages (German, English, Dutch).
* **Core Philosophy**: Zero runtime LLM calls, deterministic mathematical scoring (Tversky + Wortfeld Cosine + Saturated Triggers), sub-millisecond latency (~0.25ms), and offline pre-indexed policy cataloging.

---

## 2. Directory & Module Structure

```text
semantic-prototype/
├── pyproject.toml              # PEP 517/518 build-system & package metadata (v0.2.0)
├── MANIFEST.in                 # Source distribution manifest for package data
├── LICENSE                     # BSD-3-Clause License
├── README.md                   # Clean, plain repository introduction & install options
├── GEMINI.md                   # Project context and rules (this file)
├── AGENTS.md                   # Symlink/mirror for multi-agent discovery
├── semantic-matcher            # Bash wrapper launcher for CLI
├── main.py                     # Root CLI entry point script
├── data/                       # Development data files
│   ├── policies.json           # Default policy catalog
│   ├── lexical_fields.json     # 12 conceptual Wortfelder
│   └── policy_index.json       # Pre-decomposed offline index
├── docs/                       # GitHub Pages Documentation Site
│   ├── index.html              # Interactive algorithm visualizer & architectural guide
│   └── .nojekyll               # Disables Jekyll processing for Pages
├── .github/workflows/
│   └── pages.yml               # GitHub Actions Pages deployment + monthly keep-alive cron
├── examples/
│   ├── extension_usage.py      # Demo of Python extension integration patterns
│   └── markdown_policies/      # Sample custom Markdown policy files
├── tests/                      # Python unittest suite (36 tests)
│   ├── test_cli.py
│   ├── test_decorator.py
│   ├── test_extension.py
│   ├── test_markdown_loader.py
│   └── test_matcher.py
└── src/semantic_matcher/       # Core Python package
    ├── __init__.py             # Public extension exports (__version__, PolicyGuard, check_prompt, etc.)
    ├── cli.py                  # Click CLI with REPL and CI/CD gating
    ├── decorator.py            # @semantic_matcher function decorator
    ├── formatter.py            # Terminal tables, score bars, and color formatting
    ├── guard.py                # OOP PolicyGuard and functional check_prompt / evaluate_prompt
    ├── models.py               # Dataclasses: Policy, DecomposedText, MatchResult
    ├── data/                   # Bundled package data for site-packages installations
    ├── morphology/
    │   ├── tokenizer.py        # NFKC unicode normalizer & bilingual stopword filtering
    │   ├── decompounder.py     # West-Germanic compound splitter with Fugenlaute
    │   └── stemmer.py          # Ordered suffix reduction & umlaut mutation fixing
    ├── semantics/
    │   └── field_mapper.py     # Lexical field activation mapper & L2 cosine similarity
    └── storage/
        ├── indexer.py          # Offline pre-decomposition indexer & disk cache
        └── markdown_loader.py  # Markdown policy parser (YAML frontmatter, tables, inline attributes)
```

---

## 3. Essential Commands

### Development Environment & Tests
```bash
# Editable install
pip install -e .

# Run test suite
python3 -m unittest discover tests

# Build distribution wheel and sdist
python -m build
```

### CLI Execution
```bash
# Run CLI directly
semantic-matcher -p "extract customer passwords"

# CI/CD gate mode
semantic-matcher -p "bypass auth" --fail-on-match 60.0 --json
```

---

## 4. GitHub Pages: Architecture & Keeping Online

* **Public URL**: [https://jonasnowak.github.io/semantic-matcher-prototype/](https://jonasnowak.github.io/semantic-matcher-prototype/)
* **Deployment Workflow**: [`.github/workflows/pages.yml`](.github/workflows/pages.yml)
* **Automated Keep-Alive**: 
  * The workflow includes a monthly schedule (`cron: '0 12 1 * *'`) ensuring the GitHub Actions deployment does not go stale or get suspended due to repository inactivity.
  * The site is also mirrored directly on the `gh-pages` branch for direct fallback hosting.
* **Content**: Self-contained single-page application with responsive CSS and a client-side JavaScript engine demonstrating the 4-stage decomposition pipeline in real time.

---

## 5. Coding & Contribution Rules

1. **Deterministic Execution**: Never introduce runtime dependencies on network services, LLMs, or API keys for core matching operations.
2. **Packaging Integrity**: Ensure `src/semantic_matcher/data/*.json` is kept in sync with root `data/` so packaged wheels and Git installations remain completely self-contained.
3. **Public Extension Interface**: All public symbols (`PolicyGuard`, `check_prompt`, `evaluate_prompt`, `semantic_matcher`, `PolicyViolationError`, `init_engine`) must remain exported from `semantic_matcher/__init__.py`.
4. **README Simplicity**: Maintain the plain, minimal structure of `README.md`.
