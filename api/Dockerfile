# --- Image de l'API de classification des reclamations (FastAPI) ---
FROM python:3.11-slim

# Empeche Python de bufferiser stdout/stderr (logs visibles immediatement dans "docker logs")
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependances systeme minimales requises par certains paquets (ex: compilation eventuelle
# de wheels pour numpy/scipy sur des plateformes sans wheel precompile).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dependances en premier (profite du cache Docker : si seul le
# code applicatif change, cette etape n'est pas refaite).
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copie du code applicatif et des modeles entraines.
# IMPORTANT : placez vos fichiers baseline_tfidf_logreg_pipeline.joblib et ner/model-best/
# dans ./models AVANT de construire l'image (docker build), sinon l'API demarrera en
# mode degrade (voir /health).
COPY app ./app
COPY models ./models

EXPOSE 8000

# Verifie periodiquement que l'API repond (utile avec docker-compose / Railway / Render).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
