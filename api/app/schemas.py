from typing import Optional

from pydantic import BaseModel, Field


class ReclamationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texte brut de la réclamation client")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": (
                    "Mon colis TRK-2890 est arrivé à la mauvaise adresse à Sfax, "
                    "ça fait 5 jours que j'attends une solution."
                )
            }
        }
    }


class BatchRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="Liste de textes de réclamations à analyser")

    model_config = {
        "json_schema_extra": {
            "example": {
                "texts": [
                    "Le carton est arrivé écrasé et le produit à l'intérieur est cassé.",
                    "Toujours pas reçu ma commande, ça fait 20 jours de retard !",
                ]
            }
        }
    }


class ClassificationResult(BaseModel):
    reclamation_brute: str
    categorie: str
    confiance_categorie: float
    entites: dict
    priorite: str
    score_priorite: float
    declencheur_regle_dure: Optional[str] = None
    equipe_routage: str
    escalade_manager: bool


class BatchResult(BaseModel):
    total: int
    resultats: list[ClassificationResult]


class StatsResponse(BaseModel):
    total_reclamations_traitees: int
    uptime_secondes: float
    confiance_moyenne: Optional[float] = None
    par_categorie: dict
    par_priorite: dict
    par_equipe_routage: dict
    escalades_manager: int
    declencheurs_regle_dure: dict


class HealthResponse(BaseModel):
    status: str
    modele_classification_charge: bool
    modele_ner_charge: bool
    ner_mode: str
    detail: Optional[str] = None
