# Release candidate readiness

Updated 2026-09-16. Target: local verification and a deployment package. No live deployment was performed.

## Decision

**Release candidate supplied; production and full-scope sign-off withheld.** The application has expanded executable functionality and local regression evidence. Docker Engine access is denied in this environment, so PostgreSQL, Redis, Kafka, Qdrant, MinIO and monitoring have not been verified together. Configuration validation is not a runtime pass.

## Changes delivered

- Twelve separately compiled specialist graphs with objectives, execution records, timeouts and scoped permissions. Optional bounded LangChain model/tool loops gather read-only evidence. Deterministic controls own financial actions. Hosted model behavior has not been tested.
- Learned BGE embeddings, a MiniLM L12 cross-encoder, model-specific Qdrant collections, SQL evidence fallback, and review aggregates with excerpts and explicit sample uncertainty.
- Item-level refunds and replacements, cumulative rounding, concurrent quantity protection, immutable approvals and procurement organization, billing, delivery and payment-term details.
- Durable notification and domain-projection consumers, malformed-event dead letters, audited admin replay and workflow recovery controls.
- Request-size and origin enforcement, allowed hosts, production configuration guards, protected API documentation, dependency upgrades and improved keyboard/contrast behavior.
- Production Compose overlay, TLS edge configuration, separate non-superuser PostgreSQL application role, deployment instructions and full-stack/restart/broker-outage probes.

## Local evidence

| Check | Result | Boundary |
|---|---|---|
| Backend regression suite | 35 passed, 2 skipped | PostgreSQL/Redis checks require dedicated servers |
| Browser / accessibility | 4 tests passed; zero axe violations in scanned states | 15 routes, populated return approval, mobile keyboard and reflow |
| Ruff / mypy / TypeScript / Vite build | Passed | Static checks and production frontend bundle |
| Migrations | SQLite upgrade, downgrade/re-upgrade and schema check passed | Live PostgreSQL migration unverified |
| Learned retrieval | 24 cases; MRR@8 0.8903, recall@3 0.9583 | Authored English cases; model selection used this set |
| Read-load probe | 200 requests, concurrency 8, zero errors; p95 185.76 ms | Local reads; not a capacity estimate |
| Python / npm dependency audits | No known vulnerabilities reported | Package advisory snapshot; excludes images |
| Compose | Three configurations parse | No image-build or running-stack result |

See [verification](VERIFICATION.md), [accessibility](ACCESSIBILITY.md), and machine-readable files in `verification/`. Payments, shipments and catalog data remain simulated.

## Next executable gate

From a PowerShell session that can access Docker Desktop, at the project root:

```powershell
.\scripts\verify-stack.ps1
```

This uses the separate `shopilot-verification` Compose project and ports. It builds and starts the stack, probes each store and monitoring endpoint, executes an approved checkout, checks a saved approval after API restart, and tests Kafka outage/recovery. It preserves the stack and collects evidence. Do not treat the package as runtime verified until this command and the PostgreSQL/Redis CI job pass.

## Remaining release gates

1. Execute container builds, store integration, broker recovery and PostgreSQL concurrency tests on a Docker-enabled host; resolve failures and inspect service logs.
2. Exercise the production overlay on staging with real DNS/TLS and fresh volumes. Validate backup/restore, rollback, secret rotation, recovery objectives, image scans and sustained write load.
3. If model specialists are enabled, evaluate configured hosted models, prompt attacks, tool budgets, output quality, latency and billing. A fake-model contract test does not validate a provider.
4. Review screen-reader behavior manually, broader populated/error/loading states, supported browsers and real users. Automated axe scans are not accessibility certification.
5. Establish operators, alert destinations, retention/deletion policies and incident ownership. Real payment/carrier integrations need independently reviewed reconciliation and external-side-effect controls.

## Original full-scope boundaries

Multi-tenant commerce, self-service account recovery, live marketplace/payment/carrier integrations, image damage analysis, read replicas and high availability remain outside the implemented local release. Kubernetes files are templates. Procurement produces a JSON purchase order, not jurisdiction-specific tax or supplier onboarding documents. Review analysis is a transparent statistical summary, not a validated fraud detector. See [feature status](FEATURE_STATUS.md).

## Storefront update

Real representative photography and a colorful responsive collection page have been added. Browser regression and accessibility checks passed again. Review the image-source licensing boundary in [photo sources](PHOTO_SOURCES.md) before public deployment.
