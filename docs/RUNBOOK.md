# Local and deployment runbook

## Reconnect a local preview

Run `scripts/start-local.ps1` from PowerShell after dependencies are installed. It applies migrations, seeds only if needed, builds the frontend, starts the backend hidden and runs Vite preview on 5173. Close the foreground launcher with Ctrl+C when done. Data remains in `data/`; do not delete that directory to fix a connection problem.

If a port is occupied, check whether the existing ShopPilot instance is healthy before starting a duplicate. Visit `/health/ready` on port 8000. Never terminate unrelated processes to reclaim a port. A frontend refresh uses the HttpOnly refresh cookie to restore the session.

## Backend restart during a mission

Awaiting approvals remain paused in the checkpointer. Running executions are reclaimed after their 90-second lease expires. A failed dependency is shown in the UI; use the workflow's Retry action after the dependency is restored. Do not edit an approved payload to repair a quote; create a new checkout when prices change.

## Docker engine unavailable

The latest engine probe failed with permission denied at the Docker named pipe. From a PowerShell session that can access Docker Desktop, run `.\scripts\verify-stack.ps1`. It uses isolated verification ports and project volumes and collects store, monitoring, approval-restart and Kafka-outage evidence. The script leaves its stack running on port 15173. Configuration parsing alone does not establish that images run.

## Kafka outage / dead letters

Check `outbox_pending` and `dead_letters` in AI operations. Review structured service logs and persistent outbox error/attempt fields. Fix connectivity before replaying exhausted events. Use the admin Recovery panel after restoring the dependency. Supply a meaningful reason; replay and workflow recovery are role-checked and audited. Malformed envelopes must pass validation before replay, so invalid stored data cannot bypass schema checks. Never delete pending rows to silence a metric.

## Production preparation

- Replace demo secrets and disable seeding.
- Provision users with `uv run python -m scripts.create-user EMAIL NAME --role ADMIN` (password entered interactively).
- Apply migrations as a one-shot deployment job before application rollout.
- Configure managed stateful stores, TLS, network policies and workload identity.
- Configure provider model IDs and price estimates explicitly; zero cost settings are not a claim of free model usage.
- Enable tracing only after reviewing/redacting customer data fields.
- Run the PostgreSQL/Redis and full Docker integration jobs and perform staged failure testing.
- Review image/package security reports; pin deployment images to reviewed digests.

Rollback application images only when schema compatibility is established. Financial records and outbox/checkpoint state must be preserved across rollback; use backups and forward repair for data corruption. Real provider payment flows require a separate reviewed reconciliation runbook.


## Production overlay package

This is a staging/release-candidate configuration, not a verified deployment. Use a fresh Compose project and fresh volumes: the separate application database role is initialized only when PostgreSQL first initializes an empty volume. Do not reuse the development database volume or expose demo users.

1. Copy `.env.production.example` to `.env.production`. Generate independent URL-safe secrets for every blank password/secret field. URL-safe values avoid connection-string escaping problems. Set PUBLIC_HOST to the actual staging domain. Keep this file out of version control.
2. Point DNS to the intended host, permit TCP 80/443 and keep the stateful services private. Caddy obtains TLS certificates; this needs a reachable real domain. Internal services remain on the Compose network; monitoring ports bind to host loopback.
3. Review image versions/digests, resource limits, disk capacity, backups and access policies for that host. Learned models download on first migration/bootstrap; allow outbound model access or prepopulate the cache using reviewed weights.
4. Validate and start the isolated candidate:

```powershell
docker compose -p shopilot-production --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml config --quiet
docker compose -p shopilot-production --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up -d --build --wait --wait-timeout 900
```

5. Provision an administrator interactively inside the backend container using `python -m scripts.create-user EMAIL NAME --role ADMIN`. The production profile does not seed catalog data or demo identities. Import reviewed catalog data through an operator-controlled process before commerce testing; no complete supplier ingestion pipeline is included.
6. Exercise login, owned data access, approval, refund, notifications and recovery over HTTPS. Verify private MinIO object access and actual monitoring targets. Record image identifiers and database migration revision with the evidence.

## Backup, restore and rollback gate

Before upgrading a populated deployment, take a PostgreSQL backup including commerce, outbox, receipts and checkpoint tables and a versioned object-store backup. Restore into an isolated database and verify counts, constraints, ownership and resumable approvals before accepting the backup. Establish the recovery point/time objectives with the operator; this restore drill has not run here.

Migration `b77ffc86066b` adds item-level returns and recovery data. Its downgrade refuses when item returns exist, because the older schema cannot safely represent them. Restore a coordinated backup or use a reviewed forward repair. Do not delete financial rows to force a downgrade. Roll back application images only when their schema compatibility is demonstrated.

Model specialists remain disabled unless explicitly configured. Supply provider/key/model IDs and enable SPECIALIST_MODELS_ENABLED only after provider-specific quality and tool-boundary testing. Payment and carrier adapters in this release remain mock implementations.
