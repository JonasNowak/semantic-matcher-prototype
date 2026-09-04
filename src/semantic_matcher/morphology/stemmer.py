"""
Algorithmic Stemmer & Morphological Reducer for West-Germanic languages.
Applies rule-based suffix reduction for English and German.
"""

from typing import List

# Common stem / irregular overrides
STEM_OVERRIDES = {
    "anschlägen": "anschlag",
    "anschläge": "anschlag",
    "überwachten": "überwach",
    "überwacht": "überwach",
    "mitarbeitern": "mitarbeiter",
    "kundendaten": "kunde",
    "geheimnisse": "geheimnis",
    "passwörter": "passwort",
    "verordnungen": "verordnung",
    "prüfungen": "prüfung",
    "aktivitäten": "aktivität",
    "schwachstellen": "schwachstelle",
    "angriffe": "angriff",
    "databases": "databas",
    "extracting": "extract",
    "extracted": "extract",
    "extracts": "extract",
    "monitoring": "monitor",
    "monitored": "monitor",
    "tracking": "track",
    "tracked": "track",
    "logging": "log",
    "logged": "log",
    "breaches": "breach",
    "exploiting": "exploit",
    "exploited": "exploit",
    "exploits": "exploit",
    "bypassing": "bypass",
    "bypassed": "bypass",
    "bypasses": "bypass",
}

# German noun and verb suffixes ordered from longest to shortest
GERMAN_SUFFIXES = [
    "schaften", "igkeiten", "ungen", "heiten", "keiten",
    "schaft", "igkeit", "enden", "ender", "endes", "ieren",
    "ierten", "ung", "heit", "keit", "ende", "isch",
    "lich", "bar", "ern", "est", "ens", "end", "tet",
    "ten", "ter", "tem", "tes", "en", "er", "es", "el",
    "st", "te", "et", "ed", "em", "e", "t"
]

# English suffixes ordered from longest to shortest
ENGLISH_SUFFIXES = [
    "ational", "ization", "iveness", "fulness", "ousness",
    "ation", "ition", "alism", "iness", "ingly",
    "ment", "able", "ible", "ance", "ence", "izer",
    "ator", "ally", "ized", "ised", "iful",
    "ing", "ies", "ied", "ism", "ity", "ful",
    "ive", "ous", "ant", "ent", "est", "ers",
    "ed", "er", "es", "ly", "s"
]


def stem_word(word: str) -> str:
    """Stem a single word using rule-based suffix reduction."""
    word = word.lower().strip()
    if len(word) <= 3:
        return word

    if word in STEM_OVERRIDES:
        return STEM_OVERRIDES[word]

    # Try German suffixes first if it looks German (has umlauts or specific suffixes)
    for suffix in GERMAN_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stemmed = word[:-len(suffix)]
            # Fix umlauts caused by pluralization if at boundary
            stemmed = stemmed.replace("ä", "a").replace("ö", "o").replace("ü", "u")
            return stemmed

    # Try English suffixes
    for suffix in ENGLISH_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stemmed = word[:-len(suffix)]
            if stemmed.endswith("i"):
                stemmed = stemmed[:-1] + "y"
            return stemmed

    return word


def stem_tokens(tokens: List[str]) -> List[str]:
    """Stem a list of tokens."""
    return [stem_word(t) for t in tokens]
