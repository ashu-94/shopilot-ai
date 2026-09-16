# Scaling and production deployment

1. Use a PostgreSQL primary for orders, approvals, stock, outbox and checkpoints. Start with connection-pool sizing and appropriate indexes before considering sharding.
2. Keep replica routing behind read repositories. Never use replicas for stock checks, idempotency decisions, approval authorization or read-after-write order confirmation. The current application uses one engine.
3. Scale stateless API/MCP deployments behind ingress. PostgreSQL leases coordinate graph execution; checkpoints and approvals are shared. Run one application process per container so Prometheus process metrics are unambiguous. Scrape each pod in production.
4. Use managed Redis for caches and distributed rate limits. Cache loss cannot erase critical records. Measure hit ratio before expanding AI-result caching; this implementation does not cache private model responses.
5. Kafka consumer groups distribute event work. Partition by order ID to retain aggregate order. Use multi-broker replication and authentication in production.
6. Partition time-growing outbox/audit/event tables when retention and query volume justify it. Shard only after measuring a single primary's limit and establishing stable tenant/aggregate boundaries.
7. Use managed Qdrant and private S3 buckets with lifecycle policies, encryption and scoped workload identity.
8. External PostgreSQL/Redis/Kafka/Qdrant DNS references in the Kubernetes ConfigMap must be replaced with your actual managed endpoints. The repository intentionally does not present single-node stateful pods as a highly available production database.

The Kubernetes folder supplies deployments/services for frontend, backend and seven MCP services, a migration Job, ConfigMap, secret template, ingress/TLS reference and backend HPA. Replace image references, hostnames and secrets; apply migrations before scaling application replicas. Provision catalog and initial administrator explicitly. Test crash recovery, queue lag, stale leases, backup restoration, refunds, payment reconciliation and rolling upgrades in staging.

No throughput, availability or production latency SLO is claimed by this repository. Measure p95/p99 latency and transactional correctness under representative contention before setting targets.
