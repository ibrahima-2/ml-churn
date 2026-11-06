"""Tests unitaires : génération des données et artefacts du modèle."""
import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.generate_data import generate
from src.train import FEATURES, TARGET, build_models, evaluate

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "model.pkl"
METADATA_PATH = ROOT / "models" / "metadata.json"


def test_generated_dataset_schema():
    df = generate(n=200, seed=0)
    assert df.shape == (200, 7)
    assert list(df.columns) == FEATURES + [TARGET]
    assert df.isnull().sum().sum() == 0
    assert set(df[TARGET].unique()) <= {0, 1}


def test_generated_dataset_is_reproducible():
    pd.testing.assert_frame_equal(generate(n=100, seed=42), generate(n=100, seed=42))


def test_generated_dataset_ranges():
    df = generate(n=500)
    assert df["age"].between(18, 69).all()
    assert df["anciennete"].between(1, 119).all()
    assert (df["nb_reclamations"] >= 0).all()


def test_build_models_contains_three_models():
    assert set(build_models()) == {"logistic_regression", "decision_tree", "random_forest"}


def test_evaluate_returns_all_metrics():
    df = generate(n=300)
    model = build_models()["decision_tree"].fit(df[FEATURES], df[TARGET])
    metrics = evaluate(model, df[FEATURES], df[TARGET])
    assert set(metrics) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
    assert all(0 <= v <= 1 for v in metrics.values())


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="Modèle non entraîné (python src/train.py)")
def test_saved_model_predicts_probabilities():
    model = joblib.load(MODEL_PATH)
    X = generate(n=20)[FEATURES]
    proba = model.predict_proba(X)[:, 1]
    assert len(proba) == 20
    assert ((proba >= 0) & (proba <= 1)).all()


@pytest.mark.skipif(not METADATA_PATH.exists(), reason="Modèle non entraîné (python src/train.py)")
def test_model_metadata_is_complete():
    metadata = json.loads(METADATA_PATH.read_text())
    for key in ("model_name", "version", "trained_at", "features", "metrics", "data_sha256"):
        assert key in metadata
    assert metadata["features"] == FEATURES
    # Garde-fou qualité : un modèle moins bon que le hasard ne doit pas être livré
    assert metadata["metrics"]["roc_auc"] > 0.55
