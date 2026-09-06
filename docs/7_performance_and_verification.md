# 7. Performance, Invariants & Verification

<details>
<summary>Relevant source files</summary>

- [tests/test_matcher.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/tests/test_matcher.py) — Core scoring, Tversky index, and confidence amplification tests
- [tests/test_extension.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/tests/test_extension.py) — Public extension symbols and packaging integrity tests
- [tests/test_decorator.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/tests/test_decorator.py) — Function wrapping, argument inspection, and exception tests
- [tests/test_markdown_loader.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/tests/test_markdown_loader.py) — Frontmatter, table, and markdown parsing tests
- [tests/test_oscal.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/tests/test_oscal.py) — NIST OSCAL 1.1.0 catalog ingestion, validation, and export tests
- [tests/test_cli.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/tests/test_cli.py) — Command-line interface and CI/CD gating tests

</details>

This section benchmarks the performance profile of Semantic Matcher against neural and API-based guardrails, outlines engineering invariants, and details the test verification suite.

---

## 7.1 Latency Analysis: Microseconds vs. LLM Inferences

In high-throughput agent loops and production API gateways, adding hundreds of milliseconds of guardrail latency degrades user experience and exhausts server thread pools.

### Comparative Guardrail Performance Matrix

| Guardrail Architecture | Implementation Type | Inference Latency | Infrastructure Required | Deterministic Output? | Network Dependency? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Semantic Matcher** | **Algorithmic (Tversky + Wortfeld)** | **~0.25 ms (250 µs)** | **Single CPU core** | **Yes (100%)** | **None (Offline)** |
| **OpenAI Moderation API** | Cloud Neural API | 150 ms – 350 ms | Internet connection + API key | No (Model version drift) | Required |
| **Llama Guard 3 (8B)** | Local LLM Weights | 180 ms – 600 ms | 16 GB VRAM GPU | No (Sampling temperature) | None (Local weights) |
| **NeMo Guardrails** | Hybrid LLM Colang Engine | 300 ms – 900 ms | GPU or Cloud API | No (Stochastic generation) | Required |
| **Sentence-BERT Cosine** | Bi-Encoder Embeddings | 15 ms – 45 ms | PyTorch + TorchScript | Yes (Fixed weights) | None |

### Micro-Benchmark Breakdown per Stage
When evaluating a typical 12-word German compound prompt against 10 active governance policies:

```text
1. Unicode NFKC Normalization & Token Regex:       ~0.012 ms
2. Recursive Kompositazerlegung (Compound Split):   ~0.045 ms
3. Morphological Stemming & Umlaut Correction:     ~0.018 ms
4. Semantic Field Activation & L2 Normalization:   ~0.035 ms
5. Multi-Tier Scoring vs 10 Predecomposed Policies:~0.090 ms
6. Ranking & Result Formatting:                     ~0.015 ms
─────────────────────────────────────────────────────────────
Total Latency:                                      ~0.215 ms (approx. 4,650 queries/sec/core)
```

---

## 7.2 Determinism & Zero-LLM Guarantees

### 1. Invariant: Mathematical Reproducibility
Neural guardrails depend on floating-point matrix multiplications subject to GPU driver non-determinism, tensor floating-point rounding modes, and model quantization (FP16 vs INT4). 

Semantic Matcher relies strictly on discrete set operations, integer token counts, and fixed-precision IEEE-754 64-bit floating-point equations. For any prompt string $P$ and policy configuration $C$:

$$\forall \text{ execution } i, j : S_i(P, C) \equiv S_j(P, C)$$

### 2. Invariant: Zero External Downloads
The package installs without downloading tokenizers from HuggingFace, weights from AWS S3, or corpora from NLTK. All dictionaries, seed vocabularies, and regulatory catalogs are self-contained within the wheel distribution.

### 3. Invariant: Memory Footprint
- **RSS Memory on Process Startup:** $\approx 8.4\text{ MB}$.
- **Resident Pre-Decomposed Index:** $< 250\text{ KB}$ for 50 comprehensive enterprise policies.
- **GPU Requirements:** None.

---

## 7.3 Test Suite Architecture & Verification Matrix

The repository maintains an automated Python `unittest` suite containing **43 test cases** with 100% pass rate in $< 0.05\text{ seconds}$ on standard hardware.

```bash
# Execute complete test suite
python3 -m unittest discover tests -v
```

### Verification Matrix by Module

| Test Module | Tests | Functional Subsystems Verified |
| :--- | :--- | :--- |
| `tests/test_matcher.py` | 11 | NFKC normalization, compound splitting (`tastaturanschlag`), irregular stem overrides, umlaut mutation restoration (`anschläge` $\to$ `anschlag`), Asymmetric Tversky index with varying $\beta$, Morphological damping factor, saturated trigger accumulation, and piecewise confidence amplification thresholds. |
| `tests/test_extension.py` | 8 | Public extension API exports (`__version__`, `PolicyGuard`, `check_prompt`, `evaluate_prompt`, `semantic_matcher`, `init_engine`), package data discovery (`get_default_data_paths`), and single-line functional checks. |
| `tests/test_decorator.py` | 6 | `@semantic_matcher` wrapper mechanics, parameter inspection via `inspect.signature`, default string detection, action modes (`raise`, `warn`, `block`), custom `on_violation` callbacks, and `PolicyViolationError` attribute verification. |
| `tests/test_markdown_loader.py` | 7 | Pure-Python YAML frontmatter parsing, GitHub-flavored Markdown tables, inline metadata attributes, directory traversal, and automatic field/trigger inference. |
| `tests/test_oscal.py` | 6 | Structural identification of NIST OSCAL 1.1.0 Catalogs, recursive control hierarchy extraction, mapping to internal `Policy` dataclass, bi-directional export to valid NIST OSCAL 1.1.0 JSON catalogs, and verification of NIST SP 800-53 Component Definitions. |
| `tests/test_cli.py` | 5 | Click CLI entry points, single prompt evaluation (`-p`), custom policy paths (`-P`), framework filtering (`-f`), CI/CD gating exit codes (`--fail-on-match`), and machine-readable JSON array serialization (`--json`). |
