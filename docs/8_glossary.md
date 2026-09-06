# 8. Glossary & Conceptual Reference

This glossary defines key linguistic, mathematical, and cybersecurity compliance terms utilized throughout Semantic Matcher and its documentation.

---

## Linguistic Terminology

### Kompositazerlegung (Compound Word Splitting)
The structural linguistic process of recursively breaking down complex agglutinative compound words into their constituent root morphemes. Prominent in West-Germanic languages (German, Dutch), where multiple nouns or adjectives fuse into single unbroken orthographic tokens.

### Fugenelement / Fugenlaute (Linking Interfixes)
Phonetic transition morphemes inserted between stems during compounding (e.g. the `"s"` in `Arbeitsplatz` or the `"en"` in `Studentenausweis`). Semantic Matcher systematically detects and discards interfixes from the set $F = \{\text{"s"}, \text{"es"}, \text{"en"}, \text{"n"}, \text{"er"}, \text{"e"}\}$.

### Umlaut Mutation (Ablaut / Vowel Mutation)
The phonological alteration of a root vowel (such as $a \to \ddot{a}$, $o \to \ddot{o}$, $u \to \ddot{u}$) caused by pluralization or verb inflection. Without restoring the root vowel, morphological stem matching drops to zero.

### Wortfeld (Lexical Field)
A structural linguistic paradigm introduced by Jost Trier in 1931 asserting that human vocabulary is organized into conceptual fields that collectively partition human domain knowledge. Semantic Matcher organizes security and governance terminology into 13 conceptual Wortfelder.

### Stopword
A functional, non-content-bearing word (such as articles, prepositions, and modal auxiliaries) filtered out of natural language text to prevent distortion in set-theoretic overlap calculations.

---

## Mathematical & Algorithmic Terminology

### Asymmetric Tversky Index
A generalization of the Jaccard index formulated by Amos Tversky (1977). In Semantic Matcher, setting $\beta = 0.05$ creates an asymmetric set comparison where a short prompt is not penalized for omitting concepts found in an extensive 100-word policy document.

### Euclidean $L_2$ Normalization
Dividing a vector by its Euclidean length $\|\vec{v}\|_2 = \sqrt{\sum v_i^2}$, projecting the vector onto the unit hypersphere. Normalizing vectors ensures that cosine similarity between two unit vectors reduces to a fast dot product $\vec{u} \cdot \vec{v}$.

### Morphological Damping Factor ($\gamma$)
A scalar attenuation multiplier ($\gamma \in [0.4, 1.0]$) applied to raw semantic field cosine similarity. Damping prevents short, ambiguous prompts with high field alignment from generating false alarms unless substantiated by actual lexical or morphological overlap with the policy.

### Saturated Trigger Function
A piece-wise linear accumulation function that sums trigger keyword weights and saturates at a ceiling of 3.0:
$$S_{\text{trigger}} = \min\left(1.0, \, \frac{\sum w}{3.0}\right)$$
This ensures that high-signal indicators saturate the trigger score cleanly without numerical instability.

### Confidence Amplification
A non-linear piecewise calibration applied to the composite multi-signal score. If high-confidence indicators are detected, the score is amplified into the range $[78\%, 100\%]$, producing a bimodal distribution that clearly separates benign queries from genuine violations.

---

## GRC & Compliance Terminology

### NIST OSCAL (Open Security Controls Assessment Language)
A standardized, machine-readable JSON, YAML, and XML framework developed by the National Institute of Standards and Technology (NIST) for expressing security control baselines, catalogs, and system security plans.

### NIST SP 800-53
NIST Special Publication 800-53: *Security and Privacy Controls for Information Systems and Organizations*. Semantic Matcher implements controls including SI-4 (Information System Monitoring), SC-7 (Boundary Protection), and AC-3 (Access Enforcement).

### System Security Plan (SSP)
An official GRC document required under federal compliance regimes (such as FedRAMP) that details how an information system satisfies security controls. Semantic Matcher emits an official OSCAL Component Definition to automate SSP inclusion.

### OWASP Top 10 for LLMs
A cybersecurity framework published by OWASP identifying the top ten critical vulnerabilities in Large Language Model applications. Semantic Matcher provides algorithmic guardrail mitigations for LLM01 (Prompt Injection), LLM02 (Sensitive Information Disclosure), and LLM06 (Excessive Agency).
