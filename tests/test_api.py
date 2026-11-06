"""Tests de l'API (intégration API <-> modèle via le TestClient FastAPI)."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

PAYLOAD = {
    "age": 35,
    "anciennete": 5,
    "revenu": 450000,
    "nb_reclamations": 2,
    "montant_mensuel": 25000,
    "retards_paiement": 2,
}


# --- 4 tests du sujet --------------------------------------------------------

def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_model_info():
    response = client.get("/model/info")
    assert response.status_code == 200


def test_prediction():
    response = client.post("/predict", json=PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    assert "model_version" in data


# --- Tests complémentaires ---------------------------------------------------

def test_prediction_values_are_consistent():
    data = client.post("/predict", json=PAYLOAD).json()
    assert data["prediction"] in {"CHURN", "NO_CHURN"}
    assert 0.0 <= data["probability"] <= 1.0
    assert (data["prediction"] == "CHURN") == (data["probability"] > 0.5)
    assert data["duration_ms"] >= 0


def test_prediction_is_deterministic():
    first = client.post("/predict", json=PAYLOAD).json()
    second = client.post("/predict", json=PAYLOAD).json()
    assert first["probability"] == second["probability"]


def test_model_info_content():
    info = client.get("/model/info").json()
    assert info["model"] == "Random Forest"
    assert info["version"]
    assert info["features"] == list(PAYLOAD)


def test_missing_field_returns_422():
    payload = {k: v for k, v in PAYLOAD.items() if k != "age"}
    assert client.post("/predict", json=payload).status_code == 422


def test_wrong_type_returns_422():
    assert client.post("/predict", json={**PAYLOAD, "age": "trente"}).status_code == 422


def test_out_of_range_value_returns_422():
    assert client.post("/predict", json={**PAYLOAD, "age": -5}).status_code == 422
    assert client.post("/predict", json={**PAYLOAD, "retards_paiement": -1}).status_code == 422


def test_request_id_header():
    response = client.get("/health", headers={"X-Request-ID": "test-123"})
    assert response.headers["X-Request-ID"] == "test-123"


def test_metrics_endpoint_exposes_prometheus_metrics():
    client.post("/predict", json=PAYLOAD)
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body
    assert "churn_predictions_total" in body
    assert "churn_model_info" in body


def test_ui_is_served():
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "predict-form" in response.text
