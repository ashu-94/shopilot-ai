# Agents and persistence

`workflows.py` coordinates twelve independently compiled specialist graphs from `specialists.py`: shopping, search, inventory, recommendation, compatibility, budget, procurement, risk, order, refund, support and analytics. Each records objective, required output, status and timing in AgentRun and uses a scoped agent identity. A caller cannot impersonate a different tool profile. Specialists have bounded execution time and read retries.

`agent_models.py` optionally runs a separate LangChain model/tool loop for each specialist, limited to three model calls and four scoped read-tool calls. Set SPECIALIST_MODELS_ENABLED=true with an explicit provider, key and model IDs to enable it. Generated prose is advisory; deterministic handlers remain the authority for prices, policies and financial writes. A fake-model contract test verifies the loop/tool boundary; no hosted model call was tested. These are bounded collaborating specialists, not unconstrained autonomous purchasing agents.

Workflows live in `agent_executions`. A database compare-and-set claims queued or expired running jobs with a 90-second lease. Active workers renew every 15 seconds. A restarted instance can recover expired work from the shared checkpointer. A process frozen beyond the lease can overlap with a replacement worker; unique financial keys and conditional updates are the final defense against duplicate side effects.

Before financial execution, review creates an `approvals` row and calls LangGraph `interrupt`. The worker marks the execution awaiting approval only after the interrupt checkpoint is saved. A decision updates the approval atomically and queues the execution. The worker uses `Command(resume=...)` on the same thread ID. Request-information leaves the workflow paused; a reviewer can later approve or reject with a revised note. A separate requester reply endpoint is future work.

Approved requests are immutable hashes of persisted payloads. Catalog price and stock revalidation runs before transaction commit. Durable unique operation keys make node replay safe after a crash between a business commit and checkpoint write.

References: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts). Public workflow events expose only stage summaries, never model reasoning tokens.
