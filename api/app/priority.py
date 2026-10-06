"""Scoring hybride de priorité des réclamations — repris à l'identique de la
section 17 du notebook (règles métier « dures » + score continu regles/modèle).
"""
from __future__ import annotations

import re
from typing import Optional

RETARD_DUREE_PATTERN = re.compile(
    r"(\d{1,3})\s*(jour|jours|semaine|semaines|mois)\s+(?:de\s+)?retard", re.IGNORECASE
)
RETARD_DEPUIS_PATTERN = re.compile(
    r"depuis\s+(\d{1,3})\s*(jour|jours|semaine|semaines|mois)", re.IGNORECASE
)

DOMMAGE_MAJEUR_KEYWORDS = (
    "explos", "brul", "brûl", "bless", "danger", "incendie", "electrocut", "électrocut",
    "intoxicat", "grave", "hopital", "hôpital", "urgence vitale",
)
DOMMAGE_MINEUR_KEYWORDS = (
    "casse", "cassé", "cassée", "endommage", "endommagé", "abime", "abîmé",
    "defectueux", "défectueux", "raye", "rayé", "fuite", "tache",
)
PERTE_VOL_KEYWORDS = (
    "vole", "volé", "volee", "volée", "cambriol", "disparu", "disparition",
    "jamais recu", "jamais reçu", "jamais livre", "jamais livré", "introuvable",
    "colis perdu", "colis egare", "colis égaré", "envole", "envolé",
)
ERREUR_DESTINATION_KEYWORDS = (
    "mauvaise adresse", "erreur d'adresse", "erreur de destinataire",
    "livre a la mauvaise", "livré à la mauvaise", "mauvais destinataire",
    "chez quelqu'un d'autre", "faux destinataire", "adresse erronee", "adresse erronée",
)
ESCALADE_KEYWORDS = (
    "avocat", "juridique", "tribunal", "huissier", "presse", "media", "média",
    "reseaux sociaux", "réseaux sociaux", "association de consommateurs",
    "signalement", "resiliation", "résiliation", "derniere fois", "dernière fois",
    "inacceptable", "scandaleux", "remboursement immediat", "remboursement immédiat",
    "porter plainte", "plainte officielle",
)

MONTANT_PATTERN_PRIORITE = re.compile(
    r"(\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s?"
    r"(?:€|eur\b|euros?\b|dt\b|tnd\b|dinars?\b)",
    re.IGNORECASE,
)

RETARD_JOURS_SEUIL_URGENT = 14
RETARD_JOURS_SEUIL_MODERE = 3
MONTANT_SEUIL_ELEVE = 300.0

PRIORITY_WEIGHTS = {"regles": 0.8, "modele": 0.2}
PRIORITY_THRESHOLDS = {"haute": 0.55, "moyenne": 0.20}
DEFAULT_CATEGORY_SEVERITY = 0.45

PRIORITY_CATEGORY_SEVERITY: dict = {
    "PERTE_VOL": 0.85,
    "PRODUIT_ENDOMMAGE": 0.70,
    "ERREUR_DESTINATION": 0.60,
    "RETARD_LIVRAISON": 0.55,
    "RETOUR_REMBOURSEMENT": 0.55,
    "FACTURATION_PAIEMENT": 0.40,
    "QUALITE_SERVICE": 0.35,
    "AUTRE": 0.30,
}

ESCALADE_DECLENCHEURS = {"dommage_majeur", "plainte_forte"}


def _duree_en_jours(nombre: int, unite: str) -> int:
    unite = unite.lower()
    if unite.startswith("sem"):
        return nombre * 7
    if unite.startswith("mois"):
        return nombre * 30
    return nombre


def detecter_retard_jours(text: str) -> Optional[int]:
    durees = []
    for pattern in (RETARD_DUREE_PATTERN, RETARD_DEPUIS_PATTERN):
        for match in pattern.finditer(text):
            durees.append(_duree_en_jours(int(match.group(1)), match.group(2)))
    return max(durees) if durees else None


def detecter_dommage(text: str) -> tuple[bool, bool]:
    text_lower = text.lower()
    majeur = any(kw in text_lower for kw in DOMMAGE_MAJEUR_KEYWORDS)
    mineur = any(kw in text_lower for kw in DOMMAGE_MINEUR_KEYWORDS)
    return majeur, mineur


def detecter_perte_vol(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in PERTE_VOL_KEYWORDS)


def detecter_erreur_destination(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ERREUR_DESTINATION_KEYWORDS)


def detecter_escalade(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ESCALADE_KEYWORDS)


def extraire_montant_eur(text: str) -> Optional[float]:
    montants = []
    for match in MONTANT_PATTERN_PRIORITE.finditer(text):
        brut = match.group(1).strip().replace(" ", "")
        if "," in brut and "." in brut:
            brut = brut.replace(".", "").replace(",", ".")
        elif "," in brut:
            brut = brut.replace(",", ".")
        try:
            montants.append(float(brut))
        except ValueError:
            continue
    return max(montants) if montants else None


def detecter_ton_agressif(text: str, min_longueur: int = 15) -> bool:
    lettres = [c for c in text if c.isalpha()]
    if len(lettres) >= min_longueur:
        ratio_maj = sum(1 for c in lettres if c.isupper()) / len(lettres)
        if ratio_maj > 0.3:
            return True
    return text.count("!") >= 2


def score_priority(text: str, category: str, model_confidence: Optional[float] = None) -> dict:
    """Calcule la priorité de traitement d'une réclamation.

    Hybride : des règles métier "dures" (dommage majeur, retard très long, escalade
    explicite, perte/vol confirmé) forcent directement HAUTE. Sinon, un score continu
    combine des signaux textuels faibles et un signal modèle (sévérité de la catégorie
    pondérée par la confiance de prédiction).
    """
    text = text if isinstance(text, str) else ""

    retard_jours = detecter_retard_jours(text)
    dommage_majeur, dommage_mineur = detecter_dommage(text)
    escalade = detecter_escalade(text)
    perte_vol = detecter_perte_vol(text)
    erreur_destination = detecter_erreur_destination(text)
    montant_eur = extraire_montant_eur(text)
    ton_agressif = detecter_ton_agressif(text)
    categorie_severite = PRIORITY_CATEGORY_SEVERITY.get(category, DEFAULT_CATEGORY_SEVERITY)

    signaux = {
        "retard_jours_detecte": retard_jours,
        "dommage_majeur_detecte": dommage_majeur,
        "dommage_mineur_detecte": dommage_mineur,
        "plainte_forte_detectee": escalade,
        "perte_vol_detectee": perte_vol,
        "erreur_destination_detectee": erreur_destination,
        "montant_detecte_eur": montant_eur,
        "ton_agressif": ton_agressif,
        "categorie_severite": categorie_severite,
        "confiance_modele": model_confidence,
    }

    if dommage_majeur:
        return {"priorite": "HAUTE", "score": 1.0, "declencheur_regle_dure": "dommage_majeur", "signaux": signaux}
    if retard_jours is not None and retard_jours >= RETARD_JOURS_SEUIL_URGENT:
        return {"priorite": "HAUTE", "score": 1.0, "declencheur_regle_dure": "retard_urgent", "signaux": signaux}
    if escalade:
        return {"priorite": "HAUTE", "score": 1.0, "declencheur_regle_dure": "plainte_forte", "signaux": signaux}
    if perte_vol:
        return {"priorite": "HAUTE", "score": 1.0, "declencheur_regle_dure": "perte_vol_confirme", "signaux": signaux}

    points_regles = 0.0
    if dommage_mineur:
        points_regles += 0.25
    if retard_jours is not None and retard_jours >= RETARD_JOURS_SEUIL_MODERE:
        points_regles += 0.25
    if montant_eur is not None and montant_eur >= MONTANT_SEUIL_ELEVE:
        points_regles += 0.25
    if ton_agressif:
        points_regles += 0.15
    if erreur_destination:
        points_regles += 0.20
    rule_score = min(points_regles, 1.0)

    confiance_pour_score = model_confidence if model_confidence is not None else 0.5
    model_signal = categorie_severite * confiance_pour_score

    score = PRIORITY_WEIGHTS["regles"] * rule_score + PRIORITY_WEIGHTS["modele"] * model_signal
    score = round(min(max(score, 0.0), 1.0), 4)

    if score >= PRIORITY_THRESHOLDS["haute"]:
        priorite = "HAUTE"
    elif score >= PRIORITY_THRESHOLDS["moyenne"]:
        priorite = "MOYENNE"
    else:
        priorite = "BASSE"

    return {"priorite": priorite, "score": score, "declencheur_regle_dure": None, "signaux": signaux}
