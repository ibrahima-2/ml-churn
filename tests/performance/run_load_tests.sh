#!/usr/bin/env bash
# Exécute le plan JMeter pour 100, 500 et 1000 utilisateurs et génère
# un rapport HTML + un résumé (moyenne, médiane, p90, p95, débit, % erreurs).
#
# Usage :
#   tests/performance/run_load_tests.sh                 # 100 500 1000 utilisateurs
#   tests/performance/run_load_tests.sh 100 200         # paliers personnalisés
#   LOOPS=5 RAMPUP=20 tests/performance/run_load_tests.sh
#
# Si `jmeter` n'est pas installé, l'image Docker alpine/jmeter (multi-arch) est utilisée
# sur le réseau du docker-compose (cible : api:8000).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLAN="tests/performance/churn_load_test.jmx"
RESULTS="tests/performance/results"
USERS=("${@:-100 500 1000}")
read -r -a USERS <<< "${USERS[*]}"
LOOPS="${LOOPS:-10}"
RAMPUP="${RAMPUP:-10}"
JMETER_IMAGE="${JMETER_IMAGE:-alpine/jmeter:5.6.3}"
JMETER_HEAP="${JMETER_HEAP:--Xms1g -Xmx1g -XX:MaxMetaspaceSize=256m}"
COMPOSE_NETWORK="${COMPOSE_NETWORK:-ml-churn_default}"

cd "$ROOT_DIR"
mkdir -p "$RESULTS"

run_jmeter() {
  local users="$1" out="$RESULTS/${1}_users"
  rm -rf "$out" && mkdir -p "$out"
  if command -v jmeter >/dev/null 2>&1; then
    jmeter -n -t "$PLAN" \
      -Jhost="${HOST:-localhost}" -Jport="${PORT:-8000}" \
      -Jthreads="$users" -Jrampup="$RAMPUP" -Jloops="$LOOPS" \
      -l "$out/results.jtl" -j "$out/jmeter.log" -e -o "$out/report"
  else
    # Image native (arm64/amd64) et heap bornée : une image amd64 émulée sur
    # Apple Silicon dépasse 5 Go de RAM à 1000 threads et se fait tuer (OOM, 137).
    docker run --rm --network "$COMPOSE_NETWORK" -e HEAP="$JMETER_HEAP" --entrypoint jmeter \
      -v "$ROOT_DIR:/work" -w /work "$JMETER_IMAGE" \
      -n -t "$PLAN" \
      -Jhost="${HOST:-api}" -Jport="${PORT:-8000}" \
      -Jthreads="$users" -Jrampup="$RAMPUP" -Jloops="$LOOPS" \
      -l "$out/results.jtl" -j "$out/jmeter.log" -e -o "$out/report"
  fi
}

for users in "${USERS[@]}"; do
  echo "=== $users utilisateurs (ramp-up ${RAMPUP}s, ${LOOPS} requêtes/utilisateur) ==="
  run_jmeter "$users"
done

python3 "$SCRIPT_DIR/summarize.py" "$RESULTS"
