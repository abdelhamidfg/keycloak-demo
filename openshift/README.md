# OpenShift manifests

Run `python3 scripts/render-openshift.py --namespace commerce-demo --apps-domain apps.cluster.example.com` from the repository root to generate `.runtime/openshift.json`.

The generated Kubernetes List is directly consumable by `oc apply -f`. It contains Deployments, Services, TLS Routes, binary Docker BuildConfigs, ImageStreams, a runtime frontend ConfigMap, and Secrets for the realm and credentials. Rendering generates fresh credentials; the file has mode 0600 and is ignored by Git.

Use `scripts/deploy-openshift.sh` for the complete build and install sequence. See `docs/openshift.md` for prerequisites, updates and limitations.

`template.json` is also a checked-in OpenShift Template containing the same resources, with required parameters `NAMESPACE`, `APPS_DOMAIN`, `ADMIN_PASSWORD`, `ALICE_PASSWORD`, `BOB_PASSWORD`, `CUSTOMER_SECRET` and `ORDER_SECRET`. It can be processed with `oc process -f openshift/template.json --param-file=<private-parameter-file>`. All parameters must be supplied. The generated resources still require binary builds; the installer is the simpler complete path.
