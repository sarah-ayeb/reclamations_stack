"""Agrégateur de statistiques en mémoire pour GET /api/stats.

Simple et thread-safe (verrou), suffisant pour un seul processus/worker. Pour un
déploiement multi-workers ou persistant entre redémarrages, remplacer ce module par
un backend partagé (Redis, base de données) en conservant la même interface
`record(resultat)` / `snapshot()`.
"""
from __future__ import annotations

import threading
import time
from collections import Counter


class StatsTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.time()
        self.total_traite = 0
        self.par_categorie: Counter = Counter()
        self.par_priorite: Counter = Counter()
        self.par_equipe: Counter = Counter()
        self.escalades = 0
        self.declencheurs_regle_dure: Counter = Counter()
        self._somme_confiance = 0.0

    def record(self, resultat: dict) -> None:
        with self._lock:
            self.total_traite += 1
            self.par_categorie[resultat["categorie"]] += 1
            self.par_priorite[resultat["priorite"]] += 1
            self.par_equipe[resultat["equipe_routage"]] += 1
            self._somme_confiance += resultat["confiance_categorie"]
            if resultat["escalade_manager"]:
                self.escalades += 1
            if resultat["declencheur_regle_dure"]:
                self.declencheurs_regle_dure[resultat["declencheur_regle_dure"]] += 1

    def snapshot(self) -> dict:
        with self._lock:
            confiance_moyenne = (
                round(self._somme_confiance / self.total_traite, 4) if self.total_traite else None
            )
            return {
                "total_reclamations_traitees": self.total_traite,
                "uptime_secondes": round(time.time() - self._start_time, 1),
                "confiance_moyenne": confiance_moyenne,
                "par_categorie": dict(self.par_categorie),
                "par_priorite": dict(self.par_priorite),
                "par_equipe_routage": dict(self.par_equipe),
                "escalades_manager": self.escalades,
                "declencheurs_regle_dure": dict(self.declencheurs_regle_dure),
            }

    def reset(self) -> None:
        with self._lock:
            self.__init__()  # type: ignore[misc]


stats_tracker = StatsTracker()
