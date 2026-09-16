# Implementation plan

Deliver a runnable monorepo in incremental slices. Verify each slice before claiming it works.

1. Foundation: configuration, dependency locks, architecture decisions.
2. Data: transactional schema, migration, synthetic catalog, roles and demo identities.
3. Commerce: JWT auth, ownership checks, cart, atomic checkout, mock payment, shipment.
4. Reliability: cache-aside, durable idempotency, inventory concurrency, outbox.
5. Tools: seven MCP servers, argument schemas and per-agent permissions.
6. Retrieval: query planning, parallel document retrieval, hybrid scoring, evidence validation.
7. Agents: typed LangGraph supervisor, tool-driven recommendations, constrained optimization.
8. Policies: input guardrails, deterministic risk, immutable checkout approval quotes.
9. Human review: durable interrupt/resume, manager procurement approval, returns.
10. Events: Kafka outbox relay, deduplicated consumers, retries and dead letters.
11. UI: React shopping workspace, missions, catalog, comparison, checkout and operations.
12. Streaming: persisted execution events replayed through authenticated SSE.
13. Telemetry: Prometheus, OpenTelemetry and optional LangSmith.
14. Packaging: Docker Compose and local launcher.
15. Deployment: Kubernetes templates and CI.
16. Verification: automated integration/workflow/security/concurrency tests and browser QA.

See FEATURE_STATUS.md for delivered status and verification boundaries.
