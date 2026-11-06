"""API FastAPI de prédiction du churn.

Lancement (depuis la racine du projet) :
    uvicorn api.main:app --reload
"""
import json
import os
import time
import uuid
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict, Field

from api.logging_config import setup_logging

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "models" / "model.pkl"))
METADATA_PATH = Path(os.getenv("MODEL_METADATA_PATH", MODEL_PATH.with_name("metadata.json")))
FRONTEND_DIR = ROOT / "frontend"
APP_VERSION = "1.0.0"

logger = setup_logging()

# --------------------------------------------------------------------------
# Chargement du modèle et de ses métadonnées
# --------------------------------------------------------------------------
DEFAULT_FEATURES = [
    "age", "anciennete", "revenu", "nb_reclamations", "montant_mensuel", "retards_paiement",
]

try:
    metadata = json.loads(METADATA_PATH.read_text())
except (OSError, json.JSONDecodeError):
    metadata = {"model_name": "Random Forest", "version": "1.0.0", "features": DEFAULT_FEATURES}

MODEL_NAME = metadata.get("model_name", "Random Forest")
MODEL_VERSION = os.getenv("MODEL_VERSION", metadata.get("version", "1.0.0"))
FEATURES = metadata.get("features", DEFAULT_FEATURES)
THRESHOLD = float(metadata.get("threshold", 0.5))

try:
    model = joblib.load(MODEL_PATH)
    logger.info("Model loaded", extra={"event_type": "model_loaded", "model_name": MODEL_NAME,
                                       "model_version": MODEL_VERSION, "model_path": str(MODEL_PATH)})
except Exception:  # l'API démarre quand même : /health signale l'indisponibilité
    model = None
    logger.exception("Model loading failed", extra={"event_type": "model_load_error",
                                                    "model_path": str(MODEL_PATH)})

# --------------------------------------------------------------------------
# Métriques Prometheus métier (en plus des métriques HTTP de l'Instrumentator)
# --------------------------------------------------------------------------
PREDICTIONS = Counter(
    "churn_predictions_total", "Nombre de prédictions réalisées",
    ["prediction", "model_version"],
)
PREDICTION_ERRORS = Counter(
    "churn_prediction_errors_total", "Nombre d'erreurs de prédiction", ["model_version"],
)
PREDICTION_PROBABILITY = Histogram(
    "churn_prediction_probability", "Distribution des probabilités de churn prédites",
    ["model_version"], buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
PREDICTION_LATENCY = Histogram(
    "churn_prediction_duration_seconds", "Durée d'inférence du modèle",
    ["model_version"], buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
MODEL_INFO = Gauge("churn_model_info", "Modèle actuellement servi", ["model_name", "model_version"])
MODEL_INFO.labels(MODEL_NAME, MODEL_VERSION).set(1 if model is not None else 0)

# --------------------------------------------------------------------------
# Schémas
# --------------------------------------------------------------------------
EXAMPLE = {
    "age": 35, "anciennete": 5, "revenu": 450000,
    "nb_reclamations": 2, "montant_mensuel": 25000, "retards_paiement": 2,
}


class ClientData(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE]})

    age: int = Field(..., ge=18, le=100, description="Âge du client")
    anciennete: int = Field(..., ge=0, le=600, description="Ancienneté en mois")
    revenu: float = Field(..., ge=0, description="Revenu (FCFA)")
    nb_reclamations: int = Field(..., ge=0, le=100, description="Nombre de réclamations")
    montant_mensuel: float = Field(..., ge=0, description="Facture mensuelle (FCFA)")
    retards_paiement: int = Field(..., ge=0, le=100, description="Nombre de retards de paiement")


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: str
    probability: float
    model_version: str
    duration_ms: float


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
app = FastAPI(
    title="Churn Prediction API",
    version=APP_VERSION,
    description="Prédiction du churn des clients d'un opérateur télécom.",
)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Journalise chaque requête (qui, quoi, résultat, durée) avec un identifiant."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error", extra={
            "event_type": "http_error", "request_id": request_id,
            "method": request.method, "path": request.url.path,
        })
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    if request.url.path != "/metrics":
        logger.info("HTTP request", extra={
            "event_type": "http_request",
            "request_id": request_id,
            "client_ip": client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        })
    return response


@app.get("/")
def root():
    return {
        "application": "Churn Prediction API",
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "ui": "/ui/",
    }


@app.get("/health")
def health():
    """Liveness/readiness : l'API répond ET le modèle est chargé."""
    if model is None:
        raise HTTPException(status_code=503, detail={"status": "DOWN", "model_loaded": False})
    return {"status": "UP", "model_loaded": True, "model_version": MODEL_VERSION}


@app.get("/model/info")
def model_info():
    return {
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "trained_at": metadata.get("trained_at"),
        "features": FEATURES,
        "threshold": THRESHOLD,
        "metrics": metadata.get("metrics", {}),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(data: ClientData, request: Request):
    request_id = getattr(request.state, "request_id", None)
    if model is None:
        PREDICTION_ERRORS.labels(MODEL_VERSION).inc()
        logger.error("Prediction error", extra={
            "event_type": "prediction_error", "request_id": request_id,
            "model_version": MODEL_VERSION, "error": "model not loaded",
        })
        raise HTTPException(status_code=503, detail="Modèle indisponible")

    features = data.model_dump()
    start = time.perf_counter()
    try:
        # DataFrame avec les noms de colonnes : même format qu'à l'entraînement
        X = pd.DataFrame([features], columns=FEATURES)
        probability = float(model.predict_proba(X)[0][1])
    except Exception as exc:
        PREDICTION_ERRORS.labels(MODEL_VERSION).inc()
        logger.error("Prediction error", exc_info=True, extra={
            "event_type": "prediction_error", "request_id": request_id,
            "model_version": MODEL_VERSION, "error": str(exc), "features": features,
        })
        raise HTTPException(status_code=500, detail="Erreur lors de la prédiction")

    duration = time.perf_counter() - start
    prediction = "CHURN" if probability > THRESHOLD else "NO_CHURN"

    PREDICTIONS.labels(prediction, MODEL_VERSION).inc()
    PREDICTION_PROBABILITY.labels(MODEL_VERSION).observe(probability)
    PREDICTION_LATENCY.labels(MODEL_VERSION).observe(duration)

    logger.info(f"Prediction request: model_version={MODEL_VERSION}", extra={
        "event_type": "prediction",
        "request_id": request_id,
        "client_ip": client_ip(request),
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "prediction": prediction,
        "probability": round(probability, 4),
        "response_time_ms": round(duration * 1000, 2),
        "features": features,
    })

    return {
        "prediction": prediction,
        "probability": round(probability, 4),
        "model_version": MODEL_VERSION,
        "duration_ms": round(duration * 1000, 2),
    }


# Interface web (servie par l'API : même origine, pas de CORS à gérer)
if FRONTEND_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")

# Expose /metrics (requêtes, latences, codes HTTP) pour Prometheus
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)
