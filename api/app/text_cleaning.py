"""Nettoyage de texte — repris à l'identique de la section 5 (et 18.0) du notebook,
pour garantir que le texte vu par le modèle en production est prétraité exactement
comme lors de l'entraînement.
"""
import re
import unicodedata

TRACKING_PATTERN = re.compile(r"\bTRK-\w+\b", flags=re.IGNORECASE)
MULTI_SPACE_PATTERN = re.compile(r"\s+")
CENSORSHIP_PATTERN = re.compile(r"\*{2,}")


def _base_clean(text: str) -> str:
    """Nettoyage structurel commun (pas de perte de signal sémantique)."""
    text = unicodedata.normalize("NFKC", str(text))
    text = TRACKING_PATTERN.sub("__TRACKING__", text)
    text = CENSORSHIP_PATTERN.sub(" __CENSURE__ ", text)
    text = MULTI_SPACE_PATTERN.sub(" ", text).strip()
    return text


def clean_text_classic(text: str) -> str:
    """Nettoyage appuyé utilisé par le pipeline TF-IDF + LogReg : lowercase,
    ponctuation isolée retirée."""
    text = _base_clean(text)
    text = text.lower()
    text = re.sub(r"[^\w\s_]", " ", text, flags=re.UNICODE)
    text = MULTI_SPACE_PATTERN.sub(" ", text).strip()
    return text
