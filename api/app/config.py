"""Configuration centralisée de l'API.

Tous les chemins sont surchargeables via variables d'environnement, pour pouvoir
pointer vers les artefacts entraînés dans le notebook (section 15 : téléchargement
des artefacts / section 18.0 : rechargement rapide) sans modifier le code.
"""
import os
from pathlib import Path

# Répertoire racine où sont attendus les artefacts entraînés dans le notebook :
#   - baseline_tfidf_logreg_pipeline.joblib  (section 10 / 15)
#   - ner/model-best/                        (section 16.5 / 15)
MODELS_DIR = Path(os.getenv("MODELS_DIR", Path(__file__).resolve().parent.parent / "models"))

BASELINE_MODEL_PATH = Path(
    os.getenv("BASELINE_MODEL_PATH", MODELS_DIR / "baseline_tfidf_logreg_pipeline.joblib")
)
NER_MODEL_PATH = Path(os.getenv("NER_MODEL_PATH", MODELS_DIR / "ner" / "model-best"))

API_TITLE = "API de classification des réclamations"
API_DESCRIPTION = (
    "Classification automatique, extraction d'entités, scoring de priorité et routage "
    "des réclamations clients — expose le pipeline `traiter_reclamation` du notebook "
    "reclamations_classification_ameliore."
)
API_VERSION = "1.0.0"

# Taille maximale d'un lot pour /api/batch (protection mémoire/latence).
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "200"))
