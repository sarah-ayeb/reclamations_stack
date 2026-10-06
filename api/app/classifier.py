"""Chargement et inférence du pipeline baseline (TF-IDF + Logistic Regression),
section 10 / 18.0 du notebook.
"""
from __future__ import annotations

import logging

import joblib

from .text_cleaning import clean_text_classic

logger = logging.getLogger("reclamations_api")


class ClassificationError(RuntimeError):
    """Levée quand le modèle de classification ne peut pas être chargé."""


class BaselineClassifier:
    def __init__(self, model_path):
        try:
            self.pipeline = joblib.load(model_path)
        except Exception as exc:  # noqa: BLE001
            raise ClassificationError(
                f"Impossible de charger le modèle de classification depuis '{model_path}'. "
                "Placez-y le fichier baseline_tfidf_logreg_pipeline.joblib généré par le "
                "notebook (section 10, sauvegardé en section 15) avant de redémarrer l'API."
            ) from exc
        self.classes = list(self.pipeline.named_steps["clf"].classes_)
        logger.info("Modèle de classification chargé depuis %s (%d classes)", model_path, len(self.classes))

    def predict(self, text: str) -> tuple[str, float]:
        """Retourne (catégorie prédite, confiance [0-1] de cette catégorie)."""
        text_clean = clean_text_classic(text)
        categorie = str(self.pipeline.predict([text_clean])[0])
        proba_row = self.pipeline.predict_proba([text_clean])[0]
        confiance = float(proba_row.max())
        return categorie, round(confiance, 4)
