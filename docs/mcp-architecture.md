# MCP capability boundaries

Each of product, inventory, order, payment, shipping, customer and coupon runs the official MCP Python SDK as a separate Streamable HTTP process in Docker. `MCP_SERVICE` selects an explicit tool registry. Agents use `tools.call`; it enforces the allowlist before choosing a transport. In-process development calls the same validation and business registry.

The API signs a 60-second JWT capability with user, agent, tool and audience claims. The tool server validates the signature, expiration, audience, tool name and agent permissions. Customer and order lookups derive ownership from the authenticated principal, never from a free-form LLM argument.

Inventory reserve, payment create and shipment create are idempotent ensure operations on one approved atomic mock checkout. They do not each start a separate payment or consume inventory again. Inventory release maps to an approved cancellation. This contract avoids pretending a distributed saga is implemented.

Calls have a bounded HTTP timeout; logical failures are not blindly retried. Workflow retry/resume and durable financial idempotency handle retryable failures. Every tool call records safe audit metadata and Prometheus duration/outcome. Public servers should use workload identity and asymmetric capabilities or mTLS in place of sharing one HMAC secret.

Reference: [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk). The delivered dependency is pinned to the tested v1 API, even if a newer upstream major version is available.
