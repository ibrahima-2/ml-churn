"""Exploration des données de churn.

Usage (depuis n'importe quel dossier) :
    python notebooks/exploration.py

Correction par rapport au sujet : les chemins sont calculés à partir de
l'emplacement du script (plus besoin de faire `cd notebooks`), et les
figures sont enregistrées sans bloquer l'exécution (pas de plt.show()
sur une machine sans écran / en CI).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend non interactif : fonctionne sans écran

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "churn.csv"
FIGURES = ROOT / "reports" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA)

print(df.head())

print("\nDimensions :")
print(df.shape)

print("\nTypes :")
print(df.dtypes)

print("\nValeurs manquantes :")
print(df.isnull().sum())

print("\nStatistiques :")
print(df.describe())

print("\nRépartition du churn :")
print(df["churn"].value_counts())
print(df["churn"].value_counts(normalize=True).round(3))

print("\nMoyennes par classe (churn=0 / churn=1) :")
print(df.groupby("churn").mean().round(2).T)

# 1. Répartition de la variable cible
plt.figure(figsize=(6, 4))
sns.countplot(data=df, x="churn")
plt.title("Répartition des clients selon le churn")
plt.tight_layout()
plt.savefig(FIGURES / "churn_distribution.png", dpi=120)
plt.close()

# 2. Matrice de corrélation
plt.figure(figsize=(10, 6))
sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0)
plt.title("Corrélations")
plt.tight_layout()
plt.savefig(FIGURES / "correlation.png", dpi=120)
plt.close()

# 3. Distribution de chaque variable selon le churn
features = [c for c in df.columns if c != "churn"]
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
for ax, col in zip(axes.ravel(), features):
    sns.boxplot(data=df, x="churn", y=col, ax=ax)
    ax.set_title(col)
plt.suptitle("Distribution des variables selon le churn")
plt.tight_layout()
plt.savefig(FIGURES / "features_by_churn.png", dpi=120)
plt.close()

print(f"\nFigures enregistrées dans {FIGURES.relative_to(ROOT)}/")
