# Feature status

Current decision: [local release candidate; production sign-off pending](RELEASE_READINESS.md).

**Implemented** means executable code is supplied and the local path has been exercised where described. **Partial / unverified integration** means code exists but some requested behavior or external runtime verification is outstanding. **Documented only** means guidance/templates rather than an operating production capability.

| Requested capability | Status | Evidence or boundary |
|---|---|---|
| React/TS/Vite/Tailwind/Motion/Query/Zustand/Router | Implemented | Production build and browser flow verified |
| All requested page categories | Implemented | Assistant shares mission UI; tracking shares order-detail route |
| Personal shopping through approved mock order | Implemented | API and browser verification |
| Business procurement and independent approval | Implemented locally | Validated organization, cost center, billing/delivery, dates and terms; manager review and JSON PO |
| After-sales support and tickets | Implemented baseline | Owned-order lookup, manuals/policy evidence, diagnostic question; no physical certainty |
| Return/refund/replacement | Implemented locally | Selected item quantities, cumulative refund rounding, replay and concurrent cap tests |
| FastAPI/Pydantic/SQLAlchemy/Alembic | Implemented | Migrations, typed models, API tests |
| Required commerce entities | Implemented | Users, roles, categories, sellers, products, specs, stock, carts, orders, payments, shipments, returns, refunds, reviews, coupons, approvals, executions, audit logs |
| JWT/refresh/password hashing/RBAC | Implemented | Rotating cookie token, ownership and denied-role tests |
| Local registrations/account changes | Partial | Operator provisioning command; no self-service registration/reset/account edits |
| Supervisor classification and typed graph | Implemented | Rule-based router and persisted LangGraph state |
| Twelve specialized autonomous agents | Implemented bounded specialists; hosted execution unverified | Twelve compiled graphs with objectives, telemetry, timeout and optional read-tool model loops |
| Seven separate MCP servers | Implemented | Official SDK HTTP round-trip and tool registration tests |
| Inventory/payment/shipping write tools | Implemented local contract | Ensure operations share the atomic mock checkout transaction; not independent microservice sagas |
| Per-agent tool permissions | Implemented | Gateway and server enforcement with scoped signed capabilities |
| LangChain/provider abstraction | Partial / unverified external | Deterministic default and configurable compatible model calls; no hosted call tested |
| Agentic RAG pipeline | Implemented baseline | Planning, rewrite, parallel kinds, hybrid scores, diversity, source validation, excerpt compression |
| Semantic retrieval/cross-encoder reranking | Implemented locally | BGE small embeddings and MiniLM L12 ONNX reranker; 24-case evaluation |
| Qdrant | Unverified integration | Ingestion and metadata-filtered query code; SQL fallback tested |
| Grounded prices/stock/specs | Implemented | Catalog facts only, authoritative checkout revalidation |
| Review analysis | Implemented transparent baseline | Rating histogram, verified counts, aspects, excerpts, duplicate text and sample uncertainty; not fraud certification |
| Recommendation engine | Implemented baseline | Hard constraints plus rating/warranty/memory/stock/preferences scoring |
| Complete bundle budget optimization | Implemented | Exact Pareto frontier for the seeded catalog, deterministic alternative |
| Technical compatibility | Partial | Display ports, UPS headroom, explicit unknown dimensions/model-capacity caveats |
| LangGraph HITL interrupt/resume | Implemented | Runner-close/reopen test, approve/reject/request-information |
| PostgresSaver restart durability | Unverified integration | Configured in Docker/CI; file-backed SQLiteSaver restart path tested |
| Input guardrails | Partial | Obvious-injection/secret/tool-instruction heuristics; not exhaustive adversarial defense |
| Authorization/tool/business policies | Implemented | Ownership, role, immutable approved request hash, thresholds and duplicate protection |
| Risk scoring | Implemented baseline | Amount/account age/refund count used; configurable function also accepts other signals |
| Failed-payment/shipping risk signals | Implemented baseline | Durable failed-payment audit counts and historical address-change signals |
| Redis cache/sessions/cart/rate limit/locks | Unverified Redis integration | Real client code and CI tests; SQL durability/fallback tested locally |
| Durable idempotency | Implemented | Workflow request keys, order/payment/refund uniqueness and changed-body rejection |
| Prevent overselling | Implemented locally | Two-thread last-item race test; PostgreSQL CI job supplied |
| PostgreSQL primary/replica split | Documented only | Required-read repository seam; current queries use one configured engine |
| Kafka events | Unverified broker integration | Durable outbox and real producer/consumer code; local consumer dedupe tested |
| Kafka domain consumers | Implemented locally; broker unverified | Deduplicated notifications and current-state inventory/payment/analytics projections |
| Retry and dead-letter strategy | Implemented locally | Outbox retries, malformed-event records and audited admin replay/recovery UI |
| SSE progress/replay | Implemented | Authenticated stream, durable IDs, polling fallback, no raw reasoning |
| AI ops dashboard | Implemented baseline | Real workflow/tool data; unused agents show no data |
| Token/cost accounting | Partial | Successful provider usage and configurable estimates; failed provider billing cannot be inferred |
| LangSmith | Unverified external | Environment-enabled graph/model tracing, execution/run ID correlation |
| OpenTelemetry | Unverified exporter | FastAPI instrumentation and OTLP collector config; collector exports to debug logs |
| Prometheus/Grafana | Metrics implemented; dashboards unverified | App metrics endpoint exercised; provisioned Grafana panels supplied |
| MinIO/S3 | Unverified integration | Private JSON purchase-order archive; on-demand DB-derived fallback |
| Docker Compose | Configuration verified only | Engine unavailable here; CI includes full-stack smoke job |
| Kubernetes/HPA/ingress | Documented/templates only | Static manifests; external stateful-store references, replacement secrets/images required |
| CI/CD | Pipeline supplied, not run remotely | Lint/types/tests/builds/dependency audit/containers; deployment intentionally configurable |
| Evaluation | Expanded local regression | 35 backend tests, 4 browser tests, 24 learned retrieval cases; short read-load probe |
| Image damage analysis | Documented only | Future evidence input, never sole financial authority |
| Live carrier tracking/real payments | Not implemented by design | Explicit safe simulation throughout |
| Production readiness/load/failover certification | Not established | Local release candidate; engine access denied, production runtime/failover and manual release gates open |

## Phase accounting

Phases 1–3, 5, 7–9, 11–12 have working local implementations with the scope above. Phases 4 and 6 include tested local behavior plus unverified external Redis/Qdrant paths. Phases 10 and 13 include real integration code and local behavior, with brokers/exporters unverified. Phases 14–15 supply validated Compose configuration and deployment templates; they are not marked runtime complete. Phase 16 verifies the runnable local workflow and records the remaining infrastructure checks explicitly.
