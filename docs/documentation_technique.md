# Documentation technique — ML Churn API

## 1. Vue d'ensemble

L'application expose un modèle de classification (Random Forest) via une API REST. Elle prédit
si un client d'un opérateur télécom va résilier son abonnement.

```
                    UTILISATEUR
                         │
                         ▼
               ┌───────────────────┐
               │  Interface Web    │  /ui/  (HTML + JS, même origine que l'API)
               └─────────┬─────────┘
                         │ POST /predict (JSON)
                         ▼
               ┌───────────────────┐
               │  FastAPI          │  validation Pydantic, logging, métriques
               │  /predict         │
               └─────────┬─────────┘
                         │ predict_proba(DataFrame)
                         ▼
               ┌───────────────────┐
               │  Modèle ML        │  models/model.pkl + metadata.json
               │  Random Forest    │
               └───────────────────┘

  logs JSON (/app/logs/api.log) ──► Logstash ──► Elasticsearch ──► Kibana
  /metrics (Prometheus format)  ──► Prometheus (scrape 5 s) ──► Grafana
```

## 2. Composants

| Composant | Image / version | Port | Rôle |
|---|---|---|---|
| `api` | `ml-churn-api:1.0` (python:3.11-slim) | 8000 | API + interface web |
| `prometheus` | prom/prometheus:v2.53.3 | 9090 | Collecte et stockage des métriques, règles d'alerte |
| `grafana` | grafana/grafana:11.3.0 | 3000 | Dashboards (provisionnés) |
| `elasticsearch` | elasticsearch:8.15.3 | 9200 | Indexation des logs |
| `logstash` | logstash:8.15.3 | — | Lecture du fichier de logs → Elasticsearch |
| `kibana` | kibana:8.15.3 | 5601 | Recherche et visualisation des logs |
| `kibana-setup` | curlimages/curl | — | Création de la data view (one-shot) |

Volumes : `api-logs` (partagé entre l'API, en écriture, et Logstash, en lecture seule),
`prometheus-data`, `grafana-data`, `es-data` et `logstash-data` (sincedb).

## 3. Données et modèle

### 3.1 Dataset

Le dataset est synthétique et reproductible (`seed=42`, 2000 lignes). Le churn est tiré selon
une probabilité logistique :

```
score = 0.04·nb_reclamations + 0.08·retards_paiement − 0.015·anciennete + 0.00001·montant_mensuel
P(churn) = 1 / (1 + e^(−score))
```

| Variable | Type | Domaine | Effet sur le churn |
|---|---|---|---|
| `age` | int | 18–69 | aucun (bruit) |
| `anciennete` | int (mois) | 1–119 | **−** (fort) |
| `revenu` | int (FCFA) | 150 000–1 000 000 | aucun (bruit) |
| `nb_reclamations` | int | Poisson(2) | + (faible) |
| `montant_mensuel` | int (FCFA) | 5 000–75 000 | + (moyen) |
| `retards_paiement` | int | Poisson(1) | + (faible) |
| `churn` | 0/1 | — | cible (43 % de 1) |

### 3.2 Entraînement (`src/train.py`)

- Split train/test **80/20 stratifié** (`random_state=42`).
- Trois modèles comparés : régression logistique (avec `StandardScaler` dans un `Pipeline`),
  arbre de décision (`max_depth=5`) et Random Forest (200 arbres).
- Métriques : accuracy, precision, recall, F1 et ROC-AUC.
- Artefacts produits :
  - `models/model.pkl` : objet scikit-learn sérialisé avec joblib (compressé) ;
  - `models/metadata.json` : nom, version, date, liste ordonnée des features, seuil, métriques,
    empreinte SHA-256 du dataset et version de scikit-learn ;
  - `models/metrics.json` : comparaison des trois modèles.

`metadata.json` est la **source de vérité** pour l'API : ordre des colonnes, version et seuil.

## 4. API

### 4.1 Contrat

`POST /predict`

```json
{
  "age": 35,
  "anciennete": 5,
  "revenu": 450000,
  "nb_reclamations": 2,
  "montant_mensuel": 25000,
  "retards_paiement": 2
}
```

| Champ | Contraintes |
|---|---|
| `age` | entier, 18 ≤ x ≤ 100 |
| `anciennete` | entier, 0 ≤ x ≤ 600 |
| `revenu` | nombre ≥ 0 |
| `nb_reclamations` | entier, 0 ≤ x ≤ 100 |
| `montant_mensuel` | nombre ≥ 0 |
| `retards_paiement` | entier, 0 ≤ x ≤ 100 |

Réponse `200` :

```json
{"prediction": "CHURN", "probability": 0.67, "model_version": "1.0.0", "duration_ms": 12.4}
```

`prediction = "CHURN"` si `probability > threshold` (0.5 par défaut, défini dans `metadata.json`).

| Code | Cas |
|---|---|
| 200 | Prédiction réalisée |
| 422 | Corps invalide : champ manquant, mauvais type ou valeur hors bornes |
| 500 | Erreur pendant l'inférence (journalisée en `ERROR`) |
| 503 | Modèle non chargé (`/health` et `/predict`) |

Chaque réponse porte un en-tête `X-Request-ID`. Il est repris de la requête s'il y est fourni,
sinon généré. Il permet de corréler la requête avec ses logs.

### 4.2 Configuration (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `MODEL_PATH` | `models/model.pkl` | Modèle à charger |
| `MODEL_METADATA_PATH` | `<dossier du modèle>/metadata.json` | Métadonnées |
| `MODEL_VERSION` | valeur de `metadata.json` | Surcharge de la version annoncée |
| `LOG_LEVEL` | `INFO` | Niveau de log |
| `LOG_TO_FILE` | `true` | Écriture du fichier JSON |
| `LOG_DIR` | `logs/` (`/app/logs` dans Docker) | Dossier des logs |

### 4.3 Choix d'implémentation

- **Modèle chargé une seule fois** au démarrage, et non à chaque requête. Si le chargement
  échoue, l'API démarre quand même et `/health` renvoie `503`. L'orchestrateur voit le problème
  au lieu d'une boucle de redémarrages.
- **DataFrame avec noms de colonnes** pour l'inférence : même format qu'à l'entraînement, ce qui
  évite le warning *« X does not have valid feature names »* et les erreurs d'ordre de colonnes.
- **Un seul appel `predict_proba`** : la classe est déduite de la probabilité, ce qui évite de
  calculer deux fois la forêt.
- **Endpoint `def` (synchrone)** : FastAPI l'exécute dans un pool de threads, donc l'inférence,
  qui consomme du CPU, ne bloque pas la boucle asynchrone.

## 5. Observabilité

### 5.1 Logs

- **Console** : format `asctime levelname message` plus les champs contextuels (`docker compose logs api`).
- **Fichier** `api.log` : JSON, une ligne par événement, avec rotation (10 Mo × 5 fichiers).

| `event_type` | Émis par | Champs principaux |
|---|---|---|
| `model_loaded` / `model_load_error` | démarrage | `model_name`, `model_version`, `model_path` |
| `http_request` | middleware (toutes les routes sauf `/metrics`) ; niveau `INFO` (2xx/3xx), `WARNING` (4xx) ou `ERROR` (5xx) | `request_id`, `client_ip`, `user_agent`, `method`, `path`, `status_code`, `duration_ms` |
| `prediction` | `/predict` | `model_version`, `prediction`, `probability`, `response_time_ms`, `features` |
| `prediction_error` | `/predict` | `error`, `exception`, `features` |

Les **features** sont journalisées à chaque prédiction. Cela permet de détecter une dérive des
données (*data drift*) et de constituer un jeu de réentraînement. En production avec de vraies
données, il faudrait évaluer la conformité RGPD (pseudonymisation).

Le pipeline Logstash (`docker/logstash/pipeline/logstash.conf`) :

1. **input file** : lit `/logs/api.log`, codec `json`, et mémorise sa position dans le sincedb
   persistant ;
2. **filter date** : `timestamp` devient `@timestamp`, c'est-à-dire l'heure de l'événement et non
   l'heure de lecture ;
3. **filter mutate** : typage numérique des durées, de la probabilité et du code HTTP ;
4. **output elasticsearch** : un index par jour, `ml-churn-logs-YYYY.MM.dd`.

### 5.2 Métriques

| Métrique | Type | Labels | Source |
|---|---|---|---|
| `http_requests_total` | counter | `handler`, `method`, `status` (2xx/4xx/5xx) | Instrumentator |
| `http_request_duration_seconds` | histogram (buckets de 5 ms à 10 s) | `handler`, `method` | Instrumentator |
| `churn_predictions_total` | counter | `prediction`, `model_version` | API |
| `churn_prediction_errors_total` | counter | `model_version` | API |
| `churn_prediction_probability` | histogram | `model_version` | API |
| `churn_prediction_duration_seconds` | histogram | `model_version` | API |
| `churn_model_info` | gauge | `model_name`, `model_version` | API |

Requêtes PromQL principales :

```promql
sum(rate(http_requests_total{job="ml-churn-api"}[1m]))                                 # débit
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{handler="/predict"}[1m])))  # p95
sum(rate(http_requests_total{status=~"4xx|5xx"}[5m])) / sum(rate(http_requests_total[5m]))           # taux d'erreur
sum by (prediction) (rate(churn_predictions_total[5m]))                                # prédictions par classe
```

Alertes (`monitoring/prometheus/alerts.yml`) : `ApiDown`, `HighErrorRate` (plus de 5 % de 5xx),
`HighPredictLatencyP95` (plus de 500 ms) et `PredictionDrift` (part de CHURN hors de [15 %, 70 %]).

## 6. Image Docker

- Base `python:3.11-slim`. Les dépendances sont installées **avant** la copie du code, pour
  profiter du cache de couches.
- Seuls `api/`, `models/` et `frontend/` sont copiés (`.dockerignore`) : pas de `.venv`, de
  `.git`, de données ni de tests.
- L'application tourne avec un utilisateur **non-root** (`appuser`, uid 10001).
- `HEALTHCHECK` sur `/health`, utilisé par `docker compose up --wait` et par la CI.
- `--no-access-log` : l'accès est déjà journalisé, en JSON enrichi, par le middleware.

## 7. Stratégie de test

| Niveau | Fichier | Outil | Ce qui est vérifié |
|---|---|---|---|
| Unitaire | `tests/test_model.py` | pytest | Schéma et reproductibilité du dataset, métriques, artefacts du modèle, seuil qualité (ROC-AUC > 0,55) |
| API / intégration | `tests/test_api.py` | pytest + TestClient | Routes, contrat de réponse, validation 422, déterminisme, `/metrics`, `X-Request-ID`, interface |
| E2E | `tests/test_selenium.py` | Selenium + Chrome headless | Swagger, scénario « saisie → Prédire → résultat », affichage d'une erreur |
| Charge | `tests/performance/*.jmx` | JMeter | Temps de réponse, percentiles, débit, erreurs à 100, 500 et 1000 utilisateurs |
| Smoke | CI, job `docker` | curl | Le conteneur démarre, `/health` et `/predict` répondent |

## 8. Versionnement du modèle

- **Code et données** sont versionnés dans Git. Le dataset et le modèle sont légers (2 Mo) et
  sont donc commités. Au-delà de quelques dizaines de Mo, il faudrait utiliser DVC, Git LFS ou un
  registre de modèles (par exemple MLflow).
- **Modèle** : la version SemVer est écrite dans `metadata.json`, exposée par `/model/info`,
  ajoutée comme label à toutes les métriques et à chaque log de prédiction.
- **Image** : un tag par version, par exemple `ml-churn-api:1.0` (et le SHA du commit en CI).
- **Rollback** : redéployer l'image du tag précédent (`docker compose up -d` avec l'ancien tag),
  ou faire un `git revert` du commit du modèle puis relancer la CI.
