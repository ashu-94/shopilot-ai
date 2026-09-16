# Verification record

Release-candidate work: 2026-09-15 to 2026-09-16, Windows, Python 3.12 and Node 24. Locked dependencies: `uv.lock` and `frontend/package-lock.json`.

## Executed locally

- Backend: **35 passed, 2 skipped**, in `verification/backend-tests.xml`. PostgreSQL/Redis checks skip without dedicated test URLs.
- Ruff, mypy (30 backend files), TypeScript and Vite production build passed.
- SQLite migration upgrade/downgrade/re-upgrade passed. Local data was backed up before migration; Alembic schema comparison reports no new operations.
- Learned embeddings and MiniLM L12 reranking: 24 authored cases, MRR@8 **0.8903**, recall@3 **0.9583** (`verification/retrieval.json`). This set informed model selection; it is not an independent quality estimate.
- Read-load probe: 200 requests, concurrency 8, **0 errors**, p95 **185.76 ms**, about 118.65 requests/second (`verification/load.json`). A short local read workload, not sustained commerce throughput.
- Python and npm audits report no known vulnerabilities in final snapshots (`verification/python-audit.json`, `verification/npm-audit.json`). Container images were not scanned.
- Playwright: **4 tests passed**, zero axe violations across scanned states. Results: `verification/accessibility.json` and `verification/axe-findings.json`; see [accessibility scope](ACCESSIBILITY.md).
- All three Compose configurations parsed. Docker Engine returned a named-pipe permission error (`verification/docker-status.json`). No container runtime pass is claimed.

## Automated invariants

Last-item purchase contention, duplicate checkout/payment protection, quote tampering, decline rollback, ownership/role isolation, refresh rotation, durable local approval resume, independent manager procurement review, item refund rounding and concurrent quantity caps, replacement inventory, event deduplication/projections, agent impersonation denial, request origin/body limits, recovery permissions and bounded model/tool execution using a fake model.

Earlier browser verification completed the flagship home-office bundle through cart, owner approval and a synthetic order. The new return test creates its own disposable order, selects one unit, reviews the quantity, approves it and checks that one unit remains returnable.

## Reproduce

```bash
uv sync --frozen --python 3.12
uv run pytest -q --junitxml=verification/backend-tests.xml
uv run ruff check backend mcp_servers tests scripts
uv run mypy backend
uv run python -m scripts.evaluate
uv run python -m scripts.evaluate_retrieval
cd frontend
npm ci
npm run build
npx playwright install chromium
npx playwright test
npm audit --audit-level=high
```

Retrieval evaluation downloads weights on first use. Caches are excluded from the source archive. Never point test URLs at customer databases.

## Pending runtime validation

PostgreSQL locking/checkpoint restart, Redis integration/failover, Qdrant server queries, Kafka recovery, MinIO archival, monitoring/exporters, Docker builds, production TLS, hosted models, LangSmith, remote CI, Kubernetes, backup restoration and sustained write/failure testing. The supplied `scripts/verify-stack.ps1` and CI jobs make several checks executable, but have not passed here. See [release decision](RELEASE_READINESS.md).
