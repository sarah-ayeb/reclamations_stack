# --- Image du dashboard Streamlit (frontend) ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py api_client.py ./
COPY .streamlit ./.streamlit

EXPOSE 8501

# URL de l'API backend, surchargeable au lancement du conteneur
# (docker-compose la fixe a http://api:8000, Railway/Render a l'URL publique de l'API).
ENV API_BASE_URL=http://localhost:8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').status==200 else 1)"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
