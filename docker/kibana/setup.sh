#!/bin/sh
# Crée (ou met à jour) la data view Kibana "ml-churn-logs-*".
# Lancé automatiquement par le service `kibana-setup` du docker-compose.
set -e

KIBANA_URL="${KIBANA_URL:-http://kibana:5601}"

echo "Création de la data view ml-churn-logs-* dans ${KIBANA_URL}..."
curl -fsS -X POST "${KIBANA_URL}/api/data_views/data_view" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
        "override": true,
        "data_view": {
          "id": "ml-churn-logs",
          "title": "ml-churn-logs-*",
          "name": "ML Churn - logs API",
          "timeFieldName": "@timestamp"
        }
      }' > /dev/null

curl -fsS -X POST "${KIBANA_URL}/api/data_views/default" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{"data_view_id": "ml-churn-logs", "force": true}' > /dev/null

echo "Data view créée : ouvrir http://localhost:5601/app/discover depuis la machine hôte"
