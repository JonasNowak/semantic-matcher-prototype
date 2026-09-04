"""
West-Germanic Compound Word Splitter (Kompositazerlegung).
Recursively splits concatenated compound words into constituent morphemes,
accounting for linking morphemes (Fugen-s, -es, -en, -n, -er, -e).
"""

from typing import List, Optional, Set

# Linking morphemes common in German and Dutch
FUGEN: List[str] = ["s", "es", "en", "n", "er", "e"]

# Seed vocabulary of common West-Germanic morphemes (German & English)
DEFAULT_LEXICON: Set[str] = {
    # Base morphemes
    "arbeit", "arbeiter", "platz", "zeit", "mitarbeiter", "kollege", "personal",
    "belegschaft", "angestellte", "kraft", "leistung", "bewertung", "kontrolle",
    "erfassung", "protokoll", "prüfung", "vertrag", "kündigung", "lohn", "gehalt",
    "bewerbung", "kandidat", "einstellung",
    # Surveillance & Tech
    "überwachung", "überwachen", "tastatur", "anschlag", "anschläge", "anschlägen",
    "bildschirm", "kamera", "webcam", "video", "foto", "ton", "aufnahme",
    "log", "logger", "logging", "taste", "tasten", "maus", "bewegung", "klick",
    "spur", "verfolgung", "aktivität", "dauer", "pause",
    # Data & Privacy
    "daten", "datum", "schutz", "grund", "verordnung", "recht", "privat", "sphäre",
    "person", "personen", "bezogen", "identität", "ausweis", "pass", "passwort",
    "adresse", "kontakt", "email", "telefon", "nummer", "gesundheit", "patient",
    "krankheit", "biometrie", "finger", "abdruck", "gesicht", "erkennung", "kunde", "kunden",
    # Security & Exploits
    "sicherheit", "schwach", "stelle", "lücke", "angriff", "schad", "code",
    "software", "virus", "wurm", "hacker", "knacker", "zugang", "zugriff",
    "rechte", "berechtigung", "abfrage", "injektion", "überlauf", "speicher",
    "puffer", "befehl", "ausführung",
    # Corporate & Legal
    "geschäft", "geheimnis", "betrieb", "quell", "programm", "skript",
    "entwickler", "projekt", "plan", "finanz", "bericht", "analyse",
    "strategie", "richtlinie", "gesetz", "standard", "anweisung", "anordnung",
    "dokument",
    # English stems
    "key", "stroke", "keystroke", "pass", "word", "password", "screen", "shot",
    "screenshot", "data", "base", "database", "back", "door", "backdoor",
    "payload", "exploit", "token", "auth", "login", "user", "name", "username"
}


class Decompounder:
    """Splits compound words into constituent morphemes."""

    def __init__(self, vocabulary: Optional[Set[str]] = None, min_part_len: int = 3):
        self.vocabulary: Set[str] = set(DEFAULT_LEXICON)
        if vocabulary:
            self.vocabulary.update(vocabulary)
        self.min_part_len = min_part_len

    def add_words(self, words: List[str]) -> None:
        """Register additional domain words into the morpheme lexicon."""
        for w in words:
            w_clean = w.strip().lower()
            if len(w_clean) >= self.min_part_len:
                self.vocabulary.add(w_clean)

    def _split_single(self, word: str) -> Optional[List[str]]:
        """Attempt to split word into 2 or more morphemes."""
        word = word.lower().strip()
        if len(word) < 2 * self.min_part_len:
            return None

        # Try prefix matching
        for i in range(self.min_part_len, len(word) - self.min_part_len + 1):
            prefix = word[:i]
            remainder = word[i:]

            if prefix in self.vocabulary:
                # 1. Remainder is directly in vocabulary
                if remainder in self.vocabulary:
                    return [prefix, remainder]

                # 2. Remainder can be further split
                deeper = self._split_single(remainder)
                if deeper:
                    return [prefix] + deeper

            # Check with interfixes
            for fuge in FUGEN:
                if remainder.startswith(fuge) and len(remainder) > len(fuge) + self.min_part_len:
                    fuge_rest = remainder[len(fuge):]
                    if prefix in self.vocabulary:
                        if fuge_rest in self.vocabulary:
                            return [prefix, fuge_rest]
                        deeper = self._split_single(fuge_rest)
                        if deeper:
                            return [prefix] + deeper

        return None

    def split_compound(self, word: str) -> List[str]:
        """
        Decompose a word into subwords if it is a compound.
        Returns a list of parts, or [word] if no decomposition is found.
        """
        word = word.lower().strip()
        parts = self._split_single(word)
        if parts:
            # Flatten recursively if any part is still compoundable
            flattened = []
            for p in parts:
                sub = self._split_single(p)
                if sub:
                    flattened.extend(sub)
                else:
                    flattened.append(p)
            return flattened

        return [word]

    def decompose_tokens(self, tokens: List[str]) -> List[str]:
        """Decomposes a list of tokens, expanding any detected compounds."""
        result = []
        for token in tokens:
            parts = self.split_compound(token)
            result.extend(parts)
        return result
