"""Client HTTP léger vers l'API FastAPI de classification des réclamations.

Centralise tous les appels réseau pour que l'app Streamlit reste focalisée sur
l'affichage. Chaque fonction lève une APIError avec un message compréhensible
si l'API est injoignable, en erreur, ou renvoie un statut inattendu.
"""
from __future__ import annotations

import requests

DEFAULT_TIMEOUT = 15


class APIError(RuntimeError):
    """Erreur exploitable directement dans l'UI (message déjà formaté en français)."""


def _handle_response(response: requests.Response) -> dict:
    if response.status_code == 503:
        detail = response.json().get("detail", "Service indisponible.")
        raise APIError(f"Modèle non disponible côté API : {detail}")
    if response.status_code == 422:
        raise APIError("Requête invalide : vérifiez le texte saisi.")
    if response.status_code == 400:
        detail = response.json().get("detail", "Requête refusée par l'API.")
        raise APIError(detail)
    if not response.ok:
        raise APIError(f"Erreur API ({response.status_code}) : {response.text[:300]}")
    return response.json()


def get_health(base_url: str) -> dict:
    try:
        resp = requests.get(f"{base_url}/health", timeout=DEFAULT_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        raise APIError(
            f"Impossible de joindre l'API à '{base_url}'. "
            "Vérifiez qu'elle est bien lancée (uvicorn app.main:app)."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise APIError(f"L'API à '{base_url}' ne répond pas (timeout).") from exc
    return _handle_response(resp)


def classify(base_url: str, text: str) -> dict:
    try:
        resp = requests.post(f"{base_url}/api/classify", json={"text": text}, timeout=DEFAULT_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        raise APIError(f"Impossible de joindre l'API à '{base_url}'.") from exc
    return _handle_response(resp)


def classify_batch(base_url: str, texts: list[str]) -> dict:
    try:
        resp = requests.post(
            f"{base_url}/api/batch", json={"texts": texts}, timeout=DEFAULT_TIMEOUT * 4
        )
    except requests.exceptions.ConnectionError as exc:
        raise APIError(f"Impossible de joindre l'API à '{base_url}'.") from exc
    return _handle_response(resp)


def get_stats(base_url: str) -> dict:
    try:
        resp = requests.get(f"{base_url}/api/stats", timeout=DEFAULT_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        raise APIError(f"Impossible de joindre l'API à '{base_url}'.") from exc
    return _handle_response(resp)
