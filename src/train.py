"""Entraînement et comparaison des modèles de churn.

Usage (depuis la racine du projet) :
    python src/train.py
    python src/train.py --model logistic_regression --version 1.1.0

Produit :
    models/model.pkl       -> pipeline scikit-learn sérialisé (joblib)
    models/metadata.json   -> version, date, features, métriques, empreinte des données
    models/metrics.json    -> comparaison des 3 modèles
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "churn.csv"
MODELS_DIR = ROOT / "models"

TARGET = "churn"
FEATURES = [
    "age",
    "anciennete",
    "revenu",
    "nb_reclamations",
    "montant_mensuel",
    "retards_paiement",
]

MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
}


def build_models() -> dict:
    return {
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000)),
        ]),
        "decision_tree": DecisionTreeClassifier(max_depth=5, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=200, random_state=42),
    }


def evaluate(model, X_test, y_test) -> dict:
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    return {
        "accuracy": round(accuracy_score(y_test, predictions), 4),
        "precision": round(precision_score(y_test, predictions, zero_division=0), 4),
        "recall": round(recall_score(y_test, predictions, zero_division=0), 4),
        "f1": round(f1_score(y_test, predictions, zero_division=0), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Entraînement du modèle de churn")
    parser.add_argument("--model", default="random_forest", choices=list(MODEL_LABELS),
                        help="Modèle à sauvegarder pour l'API (défaut : random_forest)")
    parser.add_argument("--version", default="1.0.0", help="Version du modèle (SemVer)")
    args = parser.parse_args()

    df = pd.read_csv(DATA)
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train : {len(X_train)} lignes | Test : {len(X_test)} lignes")
    print(f"Taux de churn : train={y_train.mean():.3f} test={y_test.mean():.3f}")

    models = build_models()
    results = {}
    for name, model in models.items():
        print(f"\nEntraînement : {name}")
        model.fit(X_train, y_train)
        results[name] = evaluate(model, X_test, y_test)
        print(results[name])

    print("\nComparaison (jeu de test) :")
    print(pd.DataFrame(results).T.to_string())

    # Le sujet impose Random Forest pour la suite du TP ; le choix reste
    # paramétrable (--model) pour pouvoir déployer un autre modèle.
    selected = args.model
    model = models[selected]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "model.pkl", compress=3)

    metadata = {
        "model_name": MODEL_LABELS[selected],
        "model_key": selected,
        "version": args.version,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": FEATURES,
        "target": TARGET,
        "threshold": 0.5,
        "metrics": results[selected],
        "train_size": len(X_train),
        "test_size": len(X_test),
        "data_file": str(DATA.relative_to(ROOT)),
        "data_sha256": file_sha256(DATA),
        "sklearn_version": sklearn.__version__,
    }
    (MODELS_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    (MODELS_DIR / "metrics.json").write_text(json.dumps(results, indent=2))

    print(f"\nModèle sélectionné : {MODEL_LABELS[selected]} v{args.version}")
    print("Modèle sauvegardé dans models/model.pkl (+ metadata.json, metrics.json)")


if __name__ == "__main__":
    main()
