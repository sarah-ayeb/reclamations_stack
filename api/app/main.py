"""API REST exposant le pipeline `traiter_reclamation` du notebook :
nettoyage -> classification (TF-IDF + LogReg) -> extraction d'entités (NER) ->
scoring de priorité -> routage équipe.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .classifier import BaselineClassifier, ClassificationError
from .config import (
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
    BASELINE_MODEL_PATH,
    MAX_BATCH_SIZE,
    NER_MODEL_PATH,
)
from .entities import EntityExtractor
from .priority import score_priority
from .routing import router_equipe
from .schemas import (
    BatchRequest,
    BatchResult,
    ClassificationResult,
    HealthResponse,
    ReclamationRequest,
    StatsResponse,
)
from .stats import stats_tracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("reclamations_api")

# Etat applicatif partagé, peuplé au démarrage (voir lifespan ci-dessous).
state: dict = {"classifier": None, "entity_extractor": None, "startup_error": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        state["classifier"] = BaselineClassifier(BASELINE_MODEL_PATH)
    except ClassificationError as exc:
        logger.error(str(exc))
        state["startup_error"] = str(exc)
        state["classifier"] = None
    state["entity_extractor"] = EntityExtractor(NER_MODEL_PATH)
    yield
    state.clear()


app = FastAPI(title=API_TITLE, description=API_DESCRIPTION, version=API_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _traiter_reclamation(text: str) -> dict:
    """Equivalent de `traiter_reclamation(text)` (section 18.2 du notebook)."""
    classifier = state["classifier"]
    if classifier is None:
        raise HTTPException(
            status_code=503,
            detail=state["startup_error"] or "Modèle de classification non disponible.",
        )

    categorie, confiance = classifier.predict(text)
    entity_extractor = state["entity_extractor"]
    entites = entity_extractor.extract(text) if entity_extractor else {}

    priorite_result = score_priority(text, categorie, model_confidence=confiance)
    routage = router_equipe(categorie, priorite_result["declencheur_regle_dure"])

    resultat = {
        "reclamation_brute": text,
        "categorie": categorie,
        "confiance_categorie": confiance,
        "entites": entites,
        "priorite": priorite_result["priorite"],
        "score_priorite": priorite_result["score"],
        "declencheur_regle_dure": priorite_result["declencheur_regle_dure"],
        "equipe_routage": routage["equipe"],
        "escalade_manager": routage["escalade_manager"],
    }
    stats_tracker.record(resultat)
    return resultat


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"], summary="Santé du service")
def health() -> HealthResponse:
    classifier_ok = state["classifier"] is not None
    entity_extractor = state["entity_extractor"]
    ner_ok = bool(entity_extractor and not entity_extractor.using_fallback)
    return HealthResponse(
        status="ok" if classifier_ok else "degraded",
        modele_classification_charge=classifier_ok,
        modele_ner_charge=ner_ok,
        ner_mode="spacy" if ner_ok else "regex_fallback",
        detail=None if classifier_ok else state["startup_error"],
    )


@app.post(
    "/api/classify",
    response_model=ClassificationResult,
    tags=["Classification"],
    summary="Analyse une réclamation unique",
)
def classify(payload: ReclamationRequest) -> dict:
    return _traiter_reclamation(payload.text)


@app.post(
    "/api/batch",
    response_model=BatchResult,
    tags=["Classification"],
    summary="Analyse un lot de réclamations",
)
def classify_batch(payload: BatchRequest) -> BatchResult:
    if len(payload.texts) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Lot trop volumineux : {len(payload.texts)} textes (max {MAX_BATCH_SIZE}).",
        )
    resultats = [_traiter_reclamation(text) for text in payload.texts]
    return BatchResult(total=len(resultats), resultats=resultats)


@app.get(
    "/api/stats",
    response_model=StatsResponse,
    tags=["Monitoring"],
    summary="Statistiques globales du service",
)
def stats() -> dict:
    return stats_tracker.snapshot()
