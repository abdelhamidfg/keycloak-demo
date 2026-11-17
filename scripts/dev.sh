#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime
python3 scripts/wait-http.py "${KEYCLOAK_URL:-http://localhost:8080}/realms/commerce-demo/.well-known/openid-configuration"
mvn -B package
(cd frontend && npm ci && npm run build)
PIDS=()
cleanup() { for PID in "${PIDS[@]}"; do kill "$PID" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
java -jar customer-api/target/quarkus-app/quarkus-run.jar >.runtime/customer.log 2>&1 & PIDS+=("$!")
java -jar order-api/target/quarkus-app/quarkus-run.jar >.runtime/order.log 2>&1 & PIDS+=("$!")
(cd frontend && exec node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173 --strictPort) & PIDS+=("$!")
echo 'Frontend: http://localhost:5173 | API logs: .runtime/customer.log and .runtime/order.log'
wait
