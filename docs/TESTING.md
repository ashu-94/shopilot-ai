# Testing guide

## Local checks

```bash
uv run pytest -q
uv run ruff check backend mcp_servers tests scripts
uv run mypy backend
uv run python -m scripts.evaluate
uv run python -m scripts.evaluate_retrieval
npm --prefix frontend run build
```

The learned evaluation downloads model weights on first use. It is a 24-case authored regression set that informed model selection, not an independent production benchmark.

## Browser checks

After building the frontend:

```bash
cd frontend
npx playwright install chromium
npx playwright test
```

Playwright starts a disposable API on 8123 and frontend preview on 4173. Tests cover route accessibility scans, mobile keyboard focus/reflow and reviewed item-level returns. The user's database is not used. See [accessibility scope](ACCESSIBILITY.md), including the Windows external-server workaround.

## Live-store integration

Set isolated `TEST_DATABASE_URL`, `TEST_CHECKPOINT_URL` and `TEST_REDIS_URL` before pytest to enable PostgreSQL/Redis checks. Never reuse production credentials or databases. Without these variables, two server-dependent tests skip.

From Docker-enabled PowerShell, run `.\scripts\verify-stack.ps1` from the repository root. It validates stores, MCP, checkout, Kafka consumers, object storage and monitoring, plus approval resume after API restart and Kafka outage/recovery. This suite is supplied but has not passed in the restricted development environment.

## CI jobs

| Job | Purpose |
|---|---|
| backend | Lint, typing, pytest, evaluations and Python audit |
| postgres-integration | Pytest against dedicated PostgreSQL/Redis |
| frontend | Types/build, npm audit, Playwright and artifacts |
| containers | Build and exercise the Compose integration stack |

The workflow definition is [ci.yml](../.github/workflows/ci.yml). Supplied jobs are not claims of successful remote runs. Recorded local results and scope are in [VERIFICATION.md](VERIFICATION.md).
