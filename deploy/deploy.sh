#!/usr/bin/env bash
# Met à jour l'application sur une VM déjà installée (voir deploy/cloud-init.yaml).
# Appelé à la main sur la VM, ou par le job « deploy » de la CI via SSH.
#
#   /opt/ml-churn/deploy/deploy.sh            # dernière version de main
#   /opt/ml-churn/deploy/deploy.sh v1.0.0     # une version précise (retour arrière)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ml-churn}"
REF="${1:-main}"

cd "$APP_DIR"
git fetch --all --tags --prune --force   # --force : accepte un tag réécrit
git checkout -q "$REF"
if git show-ref --verify --quiet "refs/remotes/origin/$REF"; then
  git reset -q --hard "origin/$REF"
fi
echo "Déploiement de $(git describe --tags --always) ..."

docker compose up -d --build --remove-orphans

# Vérification : l'API doit répondre UP dans les 60 secondes
for i in $(seq 1 30); do
  if curl -fs http://localhost:8000/health >/dev/null; then
    curl -s http://localhost:8000/health; echo
    echo "Déploiement OK"
    exit 0
  fi
  sleep 2
done
echo "ERREUR : l'API ne répond pas après 60 s" >&2
docker compose logs --tail 50 api >&2
exit 1
