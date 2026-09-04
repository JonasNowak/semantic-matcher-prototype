"""Tokenizer and text normalizer for West-Germanic languages."""

import re
import unicodedata
from typing import List, Set

# Common functional stopwords for German and English
STOPWORDS: Set[str] = {
    # English
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "s", "same", "she", "should", "so", "some", "such", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves", "please", "write", "create", "make", "give", "can",
    # German
    "aber", "als", "am", "an", "auch", "auf", "aus", "bei", "bin", "bis", "bist",
    "da", "damit", "danach", "dann", "darum", "das", "dass", "dein", "deine",
    "dem", "den", "der", "des", "dessen", "deshalb", "die", "dies", "diese",
    "diesem", "diesen", "dieser", "dieses", "doch", "dort", "du", "durch",
    "ein", "eine", "einem", "einen", "einer", "eines", "einige", "einiges",
    "er", "es", "etwas", "euch", "euer", "eure", "für", "gab", "ganz", "gar",
    "gehe", "geht", "gewesen", "habe", "haben", "hat", "hatte", "hatten",
    "hier", "hin", "hinter", "ich", "ihm", "ihn", "ihr", "ihre", "ihrem",
    "ihren", "ihrer", "ihres", "im", "in", "indem", "ins", "ist", "jede",
    "jedem", "jeden", "jeder", "jedes", "jene", "jenem", "jenen", "jener",
    "jenes", "jetzt", "kann", "kannst", "können", "könnte", "machen", "man",
    "mein", "meine", "meinem", "meinen", "meiner", "meines", "mich", "mir",
    "mit", "nach", "nicht", "nichts", "noch", "nun", "nur", "ob", "oder",
    "ohne", "sehr", "sein", "seine", "seinem", "seinen", "seiner", "seines",
    "selbst", "sich", "sie", "sind", "so", "solche", "solchem", "solchen",
    "solcher", "solches", "soll", "sollte", "sondern", "sonst", "über",
    "um", "und", "uns", "unser", "unsere", "unserem", "unseren", "unserer",
    "unseres", "unter", "viel", "vom", "von", "vor", "während", "war",
    "waren", "warst", "was", "weg", "weil", "weiter", "welche", "welchem",
    "welchen", "welcher", "welches", "wenn", "wer", "werde", "werden", "wie",
    "wieder", "will", "wir", "wird", "wirst", "wo", "wollen", "wollte", "würde",
    "würden", "zu", "zum", "zur", "zwar", "zwischen", "bitte", "schreibe", "gib"
}


def normalize_text(text: str) -> str:
    """Normalize unicode and strip weird whitespace."""
    if not text:
        return ""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def tokenize(text: str, remove_stopwords: bool = True) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    text = normalize_text(text).lower()
    # Match words including German umlauts
    tokens = re.findall(r"[a-zäöüß0-9]+", text)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return tokens
