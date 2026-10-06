# Stack Docker — API + Dashboard réclamations

Ce dossier contient les deux services conteneurisés :

```
reclamations_stack/
├── api/                  # Backend FastAPI (classification, NER, priorité, routage)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   └── models/           # <-- DEPOSEZ ICI vos modeles entraines avant de builder
├── dashboard/             # Frontend Streamlit
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── api_client.py
└── docker-compose.yml     # Orchestration locale des deux services
```

## ⚠️ Étape indispensable avant de construire les images

Copiez vos modèles entraînés dans `api/models/` **avant** de lancer `docker build` — les
fichiers sont intégrés à l'image au moment du build, pas ajoutés après coup :

```
api/models/
├── baseline_tfidf_logreg_pipeline.joblib
└── ner/
    └── model-best/
```

---

## 1. Tester en local avec Docker Compose

**Prérequis** : Docker Desktop installé et lancé (Windows/Mac) ou Docker Engine (Linux).

Depuis ce dossier (`reclamations_stack/`) :

```bash
docker compose up --build
```

- `--build` force la reconstruction des images (nécessaire la première fois, ou après
  toute modification du code/des modèles).
- Les logs des deux services s'affichent mélangés dans le même terminal, préfixés par
  `api-1` / `dashboard-1`.

**Ce qu'il faut voir** :
- `reclamations_api | ... Application startup complete.`
- `reclamations_dashboard | You can now view your Streamlit app ...`

Une fois démarré :
- API : http://localhost:8000/docs
- Dashboard : http://localhost:8501

Le dashboard est déjà configuré pour joindre l'API via son nom de service Docker
(`API_BASE_URL=http://api:8000`, défini dans `docker-compose.yml`) — pas besoin de
changer l'URL dans la barre latérale quand vous testez via Docker.

**Pour arrêter** : `Ctrl+C`, puis `docker compose down` pour nettoyer les conteneurs.

**Pour reconstruire après une modification du code** :
```bash
docker compose up --build
```

**Pour voir les logs d'un seul service** :
```bash
docker compose logs -f api
docker compose logs -f dashboard
```

### Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| `dashboard` démarre mais affiche "Impossible de joindre l'API" | `api` pas encore prêt | Le `depends_on: condition: service_healthy` doit gérer ça automatiquement ; sinon relancez `docker compose up` |
| `/health` renvoie `degraded` | Modèles absents dans `api/models/` au moment du build | Ajoutez-les, puis `docker compose up --build api` |
| Port déjà utilisé (`8000` ou `8501`) | Une autre appli tourne dessus (ex: votre venv local encore actif) | Arrêtez l'autre process, ou changez le port dans `docker-compose.yml` (ex: `"8001:8000"`) |

---

## 2. Déployer sur Railway (gratuit, le plus simple)

Railway déploie **chaque Dockerfile comme un service séparé** — pas de support natif de
`docker-compose.yml` directement, donc on déploie l'API et le dashboard comme deux
services distincts dans le même projet.

1. Créez un compte sur [railway.app](https://railway.app), connectez votre GitHub.
2. Poussez ce dossier (`reclamations_stack/`) dans un dépôt GitHub.
3. Dans Railway : **New Project → Deploy from GitHub repo**, sélectionnez le dépôt.
4. Railway détecte plusieurs Dockerfiles possibles : créez **deux services** dans le
   même projet :
   - Service 1 : **Root Directory** = `api`, Railway détecte automatiquement le
     `Dockerfile` dedans.
   - Service 2 : **Root Directory** = `dashboard`, même principe.
5. Pour chaque service, dans l'onglet **Settings → Networking**, cliquez
   **"Generate Domain"** pour obtenir une URL publique (ex: `xxxx.up.railway.app`).
6. Sur le service **dashboard**, allez dans **Variables** et ajoutez :
   ```
   API_BASE_URL=https://<url-publique-du-service-api>.up.railway.app
   ```
   (utilisez l'URL générée à l'étape 5 pour le service `api`, avec `https://`)
7. Redéployez le service `dashboard` (Railway le fait souvent automatiquement à
   l'ajout d'une variable).

**Coût** : Railway offre un crédit gratuit mensuel limité (vérifiez les conditions
actuelles sur leur site — ça change parfois) ; au-delà, facturation à l'usage.

---

## 3. Déployer sur Render (gratuit, alternative)

Même principe : deux services web séparés, chacun basé sur son Dockerfile.

1. Créez un compte sur [render.com](https://render.com), connectez GitHub.
2. **New → Web Service**, sélectionnez votre dépôt.
3. Pour le service API :
   - **Root Directory** : `api`
   - **Runtime** : Docker (détecté automatiquement grâce au `Dockerfile`)
   - **Instance Type** : Free
   - Notez l'URL publique générée (ex: `https://reclamations-api.onrender.com`)
4. Répétez pour le dashboard :
   - **Root Directory** : `dashboard`
   - **Runtime** : Docker
   - **Instance Type** : Free
   - Dans **Environment**, ajoutez la variable :
     ```
     API_BASE_URL=https://reclamations-api.onrender.com
     ```

**Limite importante du plan gratuit Render** : les services gratuits se mettent en
veille après une période d'inactivité, et redémarrent (lentement, ~30-60s) au premier
appel suivant — normal, pas un bug de votre côté.

---

## Bon à savoir pour les deux plateformes

- **Les modèles doivent être commités dans le dépôt GitHub** (dans `api/models/`) pour
  que le build Docker distant les trouve — vérifiez que votre `.gitignore` ne les
  exclut pas. Si les fichiers sont volumineux (le NER spaCy peut peser plusieurs Mo),
  envisagez [Git LFS](https://git-lfs.com/) si vous dépassez les limites de taille de
  votre plan.
- Les statistiques de `/api/stats` étant en mémoire (voir `app/stats.py`), elles
  repartent à zéro à chaque redéploiement ou redémarrage du service — normal avec
  l'implémentation actuelle.
