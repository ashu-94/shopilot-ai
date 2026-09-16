# Kubernetes templates

These manifests are a deployment starting point, not a tested live cluster release.

1. Replace `REPLACE_OWNER`, `REPLACE_TAG`, endpoint references and `shopilot.example.com`.
2. Create the namespace and ConfigMap; provision real secrets through your secret manager using `secrets.example.yaml` as a key reference.
3. Provide managed PostgreSQL, Redis, Kafka, Qdrant and optional object storage. These endpoints are references, not bundled HA store deployments.
4. Run `migrate.yaml` and wait for it to complete.
5. Provision catalog/accounts explicitly with demo seeding disabled in production.
6. Apply applications, HPA and ingress; provision the TLS secret and an ingress controller first.

The backend image defaults to UID 1000. MCP probes currently check TCP readiness, while API probes check liveness and database connectivity. Strengthen tool dependency probes and add PodDisruptionBudgets and per-pod metric scraping before production.
