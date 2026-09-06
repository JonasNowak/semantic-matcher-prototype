# 3. Semantic Lexical Field Vector Space

<details>
<summary>Relevant source files</summary>

- [src/semantic_matcher/semantics/field_mapper.py](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/semantics/field_mapper.py#L1-L79) — Lexical field projection, activation weighting kernel, and L2 cosine calculation
- [data/lexical_fields.json](file:///Users/jonasnowak/Documents/repos/semantic-prototype/data/lexical_fields.json#L1-L72) — Seed lexicon vocabulary for all 13 conceptual fields

</details>

This section explains the semantic representation model utilized by Semantic Matcher. Instead of relying on multi-gigabyte dense neural embedding models (such as BERT or Ada-002) that require GPU runtimes or external API round-trips, Semantic Matcher implements a discrete, high-dimensional vector space based on structural linguistic **Wortfeldtheorie** (Lexical Field Theory).

---

## 3.1 Jost Trier's Wortfeldtheorie & Conceptual Fields

In 1931, German structural linguist Jost Trier established *Wortfeldtheorie* (Lexical Field Theory). Trier posited that vocabulary in human natural languages is not an arbitrary bag of independent words, but is organized into conceptual fields (**Wortfelder**) that collectively partition human domain knowledge. Words within a single field mutually define and constrain one another.

Semantic Matcher structures its semantic vocabulary into **13 formal conceptual fields** spanning security, governance, regulatory compliance, and system safety:

| Field Identifier | Core Conceptual Scope | Key German & English Stems |
| :--- | :--- | :--- |
| `PRIVACY` | PII protection, GDPR / DSGVO, personal identifiers, biometrics, health records | `person`, `identity`, `ssn`, `dsgvo`, `gdpr`, `biometrie`, `fingerabdruck`, `patient`, `kunde` |
| `SURVEILLANCE` | Workplace tracking, keylogging, screen recording, telemetry capture | `surveillance`, `überwachung`, `keystroke`, `tastaturanschlag`, `bildschirm`, `webcam`, `keylogger` |
| `HR_EMPLOYMENT` | Workplace relations, hiring, firing, employee metrics, labor law | `employee`, `mitarbeiter`, `personal`, `arbeitsplatz`, `kündigung`, `bewerbung`, `gehalt` |
| `SECURITY` | Exploits, vulnerabilities, attack payloads, malware, penetration | `exploit`, `vulnerability`, `schwachstelle`, `payload`, `injektion`, `malware`, `schadcode`, `overflow` |
| `PROMPT_INJECTION` | Jailbreaking, instruction override, system prompt exfiltration | `jailbreak`, `override`, `bypass`, `system prompt`, `instructions`, `anweisung`, `vergiss`, `dan` |
| `IP_SECRET` | Proprietary trade secrets, source code, confidential financials | `proprietary`, `geschäftsgeheimnis`, `betriebsgeheimnis`, `quellcode`, `source code`, `patent` |
| `CREDENTIALS` | Authentication tokens, API keys, passwords, sessions, secrets | `password`, `passwort`, `token`, `api key`, `schlüssel`, `login`, `authentifizierung`, `cookie` |
| `HIGH_STAKES_DECISION` | Automated scoring, credit underwriting, criminal sentencing | `automated decision`, `entscheidung`, `scoring`, `credit`, `bonität`, `darlehen`, `underwriting` |
| `DECEPTION` | Disinformation, deepfakes, impersonation, phishing, social engineering | `disinformation`, `deepfake`, `fälschung`, `täuschen`, `impersonate`, `phishing`, `betrug` |
| `LEGAL_COMPLIANCE` | Regulatory oversight, compliance audits, standards, liability | `regulation`, `compliance`, `konformität`, `audit`, `prüfung`, `gesetz`, `standard`, `richtlinie` |
| `MEDICAL_LEGAL_ADVICE` | High-risk unlicensed professional counsel (medical, legal, financial) | `medical`, `diagnose`, `behandlung`, `rezept`, `legal`, `anwalt`, `anlageberatung`, `finanzberatung` |
| `HARMFUL_OPS` | Weapons, explosives, toxic synthesis, physical violence, terror | `weapon`, `waffe`, `bombe`, `explosive`, `sprengstoff`, `gift`, `cbrn`, `synthesize`, `terror` |
| `RESOURCE_ABUSE` | Denial of Service (DoS/DDoS), scraping, recursion loops, quotas | `ddos`, `dos`, `flood`, `scraping`, `infinite loop`, `endlosschleife`, `exhaustion`, `brute force` |

---

## 3.2 3-Tier Multi-Weight Kernel

Located in [`src/semantic_matcher/semantics/field_mapper.py`](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/semantics/field_mapper.py#L41-L71).

When `LexicalFieldMapper` initializes, it compiles dual data structures for each field $f$:
1. `self.fields[f]`: Exact surface form vocabulary set.
2. `self.stemmed_fields[f]`: Pre-stemmed lemma set.
3. `self.compound_fragments[f]`: Multi-character roots with $|w| \ge 4$.

For an input sequence of decomposed tokens $T = [t_1, t_2, \dots, t_n]$, the raw scalar activation $A_f(T)$ for field $f$ is accumulated using a **3-tier hierarchical matching kernel**:

$$A_f(T) = \sum_{t \in T} K(t, f)$$

Where the kernel function $K(t, f)$ is defined as:

$$K(t, f) = \begin{cases}
1.0 & \text{if } t \in \text{fields}[f] \quad \text{(Direct Exact Word Match)} \\
0.8 & \text{else if } \text{stem}(t) \in \text{stemmed\_fields}[f] \quad \text{(Morphological Stem Match)} \\
0.5 & \text{else if } |t| \ge 4 \land \exists w \in \text{compound\_fragments}[f] : w \subseteq t \quad \text{(Compound Substring)} \\
0.0 & \text{otherwise}
\end{cases}$$

### Why Tiered Weights?
- **Weight 1.0 (Exact Match):** Gives maximum confidence to exact dictionary occurrences without ambiguity.
- **Weight 0.8 (Stem Match):** Accommodates morphological variation (e.g. inflected verbs or plural forms) with a slight discount for potential polysemy.
- **Weight 0.5 (Substring Match):** Captures sub-word compound roots that were not separated by decompounding (e.g. unfamiliar compound formations), providing graceful degradation without producing false alarms.

---

## 3.3 Euclidean $L_2$ Normalization & Fast Cosine Dot Product

Located in [`src/semantic_matcher/semantics/field_mapper.py`](file:///Users/jonasnowak/Documents/repos/semantic-prototype/src/semantic_matcher/semantics/field_mapper.py#L65-L79).

The raw activation dictionary yields a 13-dimensional vector:

$$\vec{A} = [A_{\text{PRIVACY}}, \, A_{\text{SURVEILLANCE}}, \, \dots, \, A_{\text{RESOURCE\_ABUSE}}] \in \mathbb{R}^{13}$$

### 3.3.1 Euclidean $L_2$ Normalization
To make semantic field comparisons length-invariant (preventing longer prompts or longer policy descriptions from artificially dominating shorter ones), the vector is normalized to the unit sphere:

$$\|\vec{A}\|_2 = \sqrt{\sum_{i=1}^{13} A_i^2}$$

$$\vec{u} = \begin{cases}
\frac{\vec{A}}{\|\vec{A}\|_2} & \text{if } \|\vec{A}\|_2 > 0 \\
\vec{0} & \text{if } \|\vec{A}\|_2 = 0
\end{cases}$$

Every component $u_i$ is rounded to 4 decimal places for numerical stability.

### 3.3.2 Fast Dot Product Equivalence
Cosine similarity between two arbitrary vectors $\vec{x}$ and $\vec{y}$ is formally defined as:

$$\cos(\vec{x}, \vec{y}) = \frac{\vec{x} \cdot \vec{y}}{\|\vec{x}\|_2 \|\vec{y}\|_2}$$

Because both the prompt vector $\vec{u}$ and the pre-computed policy vector $\vec{v}$ are **strictly unit-normalized** ($\|\vec{u}\|_2 = 1.0$ and $\|\vec{v}\|_2 = 1.0$), the denominator evaluates identically to $1.0$:

$$\cos(\vec{u}, \vec{v}) = \vec{u} \cdot \vec{v} = \sum_{i=1}^{13} u_i \cdot v_i$$

This reduces runtime cosine similarity to a simple 13-iteration floating-point multiply-accumulate loop, executing in **less than 2 microseconds** in pure Python. The resulting scalar is clamped to $[0.0, 1.0]$:

```python
@staticmethod
def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    dot_product = sum(vec1.get(k, 0.0) * vec2.get(k, 0.0) for k in vec1)
    return max(0.0, min(1.0, dot_product))
```
