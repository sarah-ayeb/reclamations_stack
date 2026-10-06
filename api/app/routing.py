"""Table de routage catégorie -> équipe — reprise à l'identique de la section 18.1."""
from typing import Optional

ROUTING_TEAM = {
    "PERTE_VOL": "Logistique",
    "ERREUR_DESTINATION": "Logistique",
    "RETARD_LIVRAISON": "Logistique",
    "PRODUIT_ENDOMMAGE": "Qualité / SAV",
    "RETOUR_REMBOURSEMENT": "Finance / Remboursements",
    "FACTURATION_PAIEMENT": "Finance / Remboursements",
    "QUALITE_SERVICE": "Service Après-Vente",
    "AUTRE": "Support général",
}
DEFAULT_TEAM = "Support général"

# Déclencheurs de règle dure qui justifient une alerte manager en plus du routage normal
# (perte_vol_confirme est déjà géré par l'équipe Logistique elle-même).
ESCALADE_DECLENCHEURS = {"dommage_majeur", "plainte_forte"}


def router_equipe(categorie: str, declencheur_regle_dure: Optional[str] = None) -> dict:
    """Détermine l'équipe cible et si une escalade manager est nécessaire."""
    return {
        "equipe": ROUTING_TEAM.get(categorie, DEFAULT_TEAM),
        "escalade_manager": declencheur_regle_dure in ESCALADE_DECLENCHEURS,
    }
