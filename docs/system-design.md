# Transaction and event design

Checkout validates the approved immutable request, obtains authoritative prices and coupon, then conditionally decrements inventory inside a SQL transaction. It inserts order lines, safe mock payment, initial shipment, audit record and domain outbox events, and consumes purchased cart quantities. All commits or all rolls back.

`UPDATE inventory SET available = available - quantity WHERE product_id = id AND available >= quantity` serializes conflicting writes on PostgreSQL row locks and rejects the losing purchase through affected-row count. Sorted product IDs reduce deadlock risk for multi-item transactions. SQLite WAL supports a local correctness demo with serialized writers, not a throughput benchmark.

Payment failure occurs before commit. A production provider cannot be included in the SQL atomic transaction; introduce pending orders, expiring reservations, provider idempotency, authenticated webhooks and a compensating saga. Treat network timeouts as unknown payment outcomes and reconcile before retrying a charge.

The outbox relay provides at-least-once delivery. It may publish twice if it crashes after Kafka acknowledgement and before marking the row; consumer receipts handle that. Consumers commit effects and deduplication receipts in one SQL transaction, then commit Kafka offsets. Malformed messages are stored as auditable dead letters. Consumers persist in-app notifications and domain projections; they do not send external messages.

Cancellation returns sellable stock only for an unshipped confirmed order and marks mock payment voided. Refund returns do not restock damaged goods. Replacement reserves new units and creates a second shipment. Returns select individual order lines and quantities. Conditional quantity updates and cumulative rounding enforce entitlement and paid-amount caps; multiple partial returns are supported.
