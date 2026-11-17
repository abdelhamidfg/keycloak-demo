#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
NAMESPACE=${1:?Usage: scripts/deploy-openshift.sh NAMESPACE APPS_DOMAIN [EXISTING_KEYCLOAK_URL]}
APPS_DOMAIN=${2:?Supply the wildcard apps domain, e.g. apps.cluster.example.com}
EXISTING_KEYCLOAK_URL=${3:-}
oc whoami >/dev/null
if oc -n "$NAMESPACE" get deployment frontend >/dev/null 2>&1; then
  echo 'This installer requires a fresh demo namespace. For existing installs, use the update instructions in docs/openshift.md.' >&2
  exit 1
fi
oc get namespace "$NAMESPACE" >/dev/null 2>&1 || oc new-project "$NAMESPACE"
mvn -B package
RENDER_ARGS=(--namespace "$NAMESPACE" --apps-domain "$APPS_DOMAIN" --output ".runtime/$NAMESPACE/openshift.json")
if [ -n "$EXISTING_KEYCLOAK_URL" ]; then RENDER_ARGS+=(--keycloak-url "$EXISTING_KEYCLOAK_URL"); fi
python3 scripts/render-openshift.py "${RENDER_ARGS[@]}"
if [ -n "$EXISTING_KEYCLOAK_URL" ]; then
  python3 scripts/import-realm.py --keycloak-url "$EXISTING_KEYCLOAK_URL" --manifest ".runtime/$NAMESPACE/openshift.json"
fi
oc -n "$NAMESPACE" apply -f ".runtime/$NAMESPACE/openshift.json"
# Stage only build inputs; never upload generated credentials, runtime data, or .git.
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
for API in customer-api order-api; do
  mkdir -p "$STAGING/$API-context/$API/target"
  cp "$API/Dockerfile" "$STAGING/$API-context/$API/"
  cp -R "$API/target/quarkus-app" "$STAGING/$API-context/$API/target/"
done
mkdir -p "$STAGING/frontend-context/frontend"
cp frontend/package.json frontend/package-lock.json frontend/Dockerfile frontend/nginx.conf frontend/index.html "$STAGING/frontend-context/frontend/"
cp -R frontend/src frontend/public "$STAGING/frontend-context/frontend/"
for APP in customer-api order-api frontend; do
  oc -n "$NAMESPACE" start-build "$APP" --from-dir="$STAGING/$APP-context" --follow --wait
  oc -n "$NAMESPACE" rollout restart "deployment/$APP"
done
APPS=(customer-api order-api frontend)
if [ -z "$EXISTING_KEYCLOAK_URL" ]; then APPS=(keycloak "${APPS[@]}"); fi
for APP in "${APPS[@]}"; do
  oc -n "$NAMESPACE" rollout status "deployment/$APP" --timeout=600s
done
oc -n "$NAMESPACE" get routes
printf 'Credentials are in .runtime/%s/demo-login.json\n' "$NAMESPACE"
