FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LOG_DIR=/app/logs

WORKDIR /app

# 1. Dépendances d'abord : couche mise en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Code + modèle uniquement (voir .dockerignore)
COPY api/ api/
COPY models/ models/
COPY frontend/ frontend/

# 3. Utilisateur non-root ; logs/ lui appartient (partagé avec Logstash via un volume)
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app/logs
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
