# OpenShift deployment

## Prerequisites

- OpenShift 4.x, an authenticated `oc` session, and permission to create a project and its workloads/builds/routes/secrets.
- An enabled internal image registry and Docker build strategy; build pods must reach Maven/npm and the image registries.
- Java 21 and Maven on the workstation (API jars are built locally), plus Python 3.10+.
- A wildcard application domain with a trusted router certificate. API pods must resolve and reach the public Keycloak route; the same issuer URL is used by browser and APIs.
- Approximately 5 GiB of available workload memory plus temporary build capacity.

```sh
oc login https://api.cluster.example.com:6443
./scripts/deploy-openshift.sh commerce-demo apps.cluster.example.com
```

Use a fresh project. The installer refuses an existing Keycloak deployment to avoid silently replacing secrets while Keycloak retains an older imported realm. It creates one replica per component, TLS edge Routes with HTTP-to-HTTPS redirects, health probes, resource limits, and containers compatible with non-root execution. No `anyuid` SCC grant is required. The router terminates TLS; this demo uses HTTP between the router and service.

The installed names are `keycloak`, `customer-api`, `order-api`, and `frontend`. Each Route host is `<name>-<namespace>.<apps-domain>`. The generated manifest is `.runtime/<namespace>/openshift.json`; it is a Kubernetes List in JSON format, accepted by `oc apply`.

The renderer supports environment overrides `ADMIN_PASSWORD`, `ALICE_PASSWORD`, `BOB_PASSWORD`, `CUSTOMER_SECRET` and `ORDER_SECRET`. Otherwise it generates random values. The realm is stored in a Kubernetes Secret because it contains the demo users' initial passwords and API client credentials. Do not commit generated manifests/login files or paste their contents into logs.

## Updating application code

Keep the generated manifest and Secrets. Rebuild the API jar locally, then submit a new binary build using a clean staging directory as in the installer (only jars/Dockerfiles/frontend sources; no `.runtime/` or credentials). After a successful build:

```sh
oc -n commerce-demo rollout restart deployment/customer-api
oc -n commerce-demo rollout status deployment/customer-api
```

Repeat for the changed application. Updating the frontend ConfigMap requires restarting its pod because the mounted `config.js` uses a subPath. Never rerun the renderer and apply new secrets over a running realm without coordinating the credential changes inside Keycloak.

## Persistence and lifecycle

This is an intentionally disposable demo:

- Order API data lives in memory; restart resets orders.
- Keycloak uses a `dev-file` database on an `emptyDir`. Container restarts within the same pod retain it, but pod replacement loses it and reimports `realm.json`. Policy edits made in the console are therefore temporary.
- Keycloak runs with `start`, an explicit HTTPS hostname and trusted forwarded headers from the cluster router. Runtime augmentation is allowed for the demo image.
- One replica and `Recreate` deployments avoid inconsistent in-memory orders. Do not scale these demo workloads.

For durable deployments, replace the Keycloak deployment with the Keycloak Operator and a supported external PostgreSQL database/PVC strategy. Add a persistent order database before scaling. Export/version approved realm changes, use secret management, restrict administrator access, and configure network policies for your cluster. A cluster-specific CA should be added to the Java trust store; do not disable TLS verification.

## Troubleshooting

```sh
oc -n commerce-demo get pods,builds,routes
oc -n commerce-demo logs deployment/keycloak
oc -n commerce-demo logs deployment/customer-api
oc -n commerce-demo logs deployment/order-api
oc -n commerce-demo describe pod <pod-name>
```

- **ImagePullBackOff:** confirm internal registry availability and that the binary builds finished.
- **API startup/issuer/TLS failure:** check pod DNS, reachability of the Keycloak route, and trust of the route certificate.
- **Redirect URI failure:** use the exact frontend HTTPS root URL with trailing `/` configured in `commerce-web`.
- **401:** missing/expired token, wrong issuer, or wrong audience. Use an access token from this realm, not an ID token.
- **403 for Bob:** check `order-manager`, resource scopes, and policy logic. New role assignments require token renewal.
- **404 after deletion:** restart only the Order API to restore records.

To remove this disposable installation, explicitly delete its project when you no longer need it: `oc delete project commerce-demo`. This deletes everything in that project.

## Reusing an existing Keycloak server

Supply its public HTTPS URL as the installer's third argument. Set the administrator credentials in the environment (do not commit them):

```sh
export KC_ADMIN_USER=<administrator>
read -rs -p 'Keycloak admin password: ' KC_ADMIN_PASSWORD; echo
export KC_ADMIN_PASSWORD
./scripts/deploy-openshift.sh keycloak-demo apps.cluster.example.com https://keycloak.apps.cluster.example.com
unset KC_ADMIN_PASSWORD KC_ADMIN_USER
```

This mode creates only the frontend and API workloads. It imports a **new `commerce-demo` realm** through the existing server's Admin REST API and refuses to overwrite an existing realm. Other realms and the existing server's deployment/database are not modified. The administrator password is not written into the repository or deployment manifest. The administrative bootstrap script uses the built-in `admin-cli` client; both application clients still require Authorization Code + PKCE and have password grants disabled.

In this mode, Keycloak persistence and version are managed by the existing installation, so the disposable Keycloak storage notes above do not apply. Order API data remains in memory. The generated realm Secret stays in the demo namespace as a reproducible configuration artifact; the existing Keycloak does not mount it.

On macOS, a Python installation without a configured CA bundle may reject an otherwise valid route certificate. If needed, set `SSL_CERT_FILE=/etc/ssl/cert.pem` to use the system's trusted CA bundle. This preserves certificate validation.
