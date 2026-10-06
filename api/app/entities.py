"""Extraction d'entités (section 16 du notebook).

Utilise le modèle spaCy custom entraîné (NUMERO_TRACKING, VILLE, MONTANT, DATE) si
l'artefact est présent sur disque. Sinon, replie automatiquement sur les patterns
regex de la section 16.6bis (comparaison à une baseline regex seule) — couvre tout
sauf VILLE, qui nécessite le modèle appris — plutôt que de faire planter l'API.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("reclamations_api")

ENTITY_LABEL_TO_KEY = {
    "NUMERO_TRACKING": "tracking",
    "VILLE": "ville",
    "MONTANT": "montant",
    "DATE": "date",
}

# Formats reels observes : TRK-2025-51462, EXP-2024-11846, CMR-2023-99463, TR-2024-64516,
# ADR-2024-68487, LP-2024-79922, PKG-2025-18357, BL-2024-55808... -> prefixe generique 2-4
# lettres + annee + numero, plutot qu'un seul prefixe fige.
TRACKING_PATTERN = re.compile(r"\b[A-Z]{2,5}-\d{4}-\d{3,7}\b", flags=re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{1,2})?\s?(?:€|eur\b|euros?\b|dt\b|tnd\b|dinars?\b)",
    flags=re.IGNORECASE,
)
DATE_NUMERIC_PATTERN = re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b")
MOIS_FR = (
    "janvier", "février", "fevrier", "mars", "avril", "mai", "juin", "juillet",
    "août", "aout", "septembre", "octobre", "novembre", "décembre", "decembre",
)
DATE_TEXT_PATTERN = re.compile(
    r"\b\d{1,2}\s+(?:" + "|".join(MOIS_FR) + r")\s+\d{4}\b", flags=re.IGNORECASE
)


class EntityExtractor:
    def __init__(self, model_path):
        self.nlp = None
        self.using_fallback = True
        try:
            import spacy  # import local : évite de bloquer le démarrage si spaCy/le modèle manque

            self.nlp = spacy.load(model_path)
            self.using_fallback = False
            logger.info("Modèle NER spaCy chargé depuis %s", model_path)
        except Exception as exc:  # noqa: BLE001 - on veut dégrader proprement, quelle que soit la cause
            logger.warning(
                "Modèle NER introuvable/chargeable (%s) : repli sur l'extraction regex "
                "(VILLE non couverte dans ce mode). Détail : %s", model_path, exc,
            )

    def extract(self, text: str) -> dict:
        if self.nlp is not None:
            return self._extract_spacy(text)
        return self._extract_regex(text)

    def _extract_spacy(self, text: str) -> dict:
        doc = self.nlp(text)
        resume: dict = {}
        for ent in doc.ents:
            cle = ENTITY_LABEL_TO_KEY.get(ent.label_, ent.label_.lower())
            resume.setdefault(cle, ent.text)
        return resume

    def _extract_regex(self, text: str) -> dict:
        resume: dict = {}
        m = TRACKING_PATTERN.search(text)
        if m:
            resume["tracking"] = m.group(0)
        m = AMOUNT_PATTERN.search(text)
        if m:
            resume["montant"] = m.group(0)
        m = DATE_NUMERIC_PATTERN.search(text) or DATE_TEXT_PATTERN.search(text)
        if m:
            resume["date"] = m.group(0)
        return resume
