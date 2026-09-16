# Configuration

No external secrets are required for local mode. Copy `.env.example` only if you want to override defaults.

| Variables | Purpose |
|---|---|
| `DATABASE_URL`, `CHECKPOINT_URL` | SQLAlchemy DB URL and separate LangGraph persistence URL |
| `JWT_SECRET`, `APP_ENV`, `SEED_DEMO`, `DEMO_PASSWORD` | Auth secret and demo controls |
| `REDIS_URL`, `QDRANT_URL`, `KAFKA_BOOTSTRAP_SERVERS` | Optional local dependencies; provided by Compose |
| `MCP_TRANSPORT`, `MCP_HOST` | `inprocess` locally; `http` and `mcp` in Compose |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL` | `deterministic` by default; any configured OpenAI-compatible endpoint when enabled |
| `LLM_FAST_MODEL`, `LLM_ADVANCED_MODEL`, `SPECIALIST_MODELS_ENABLED` | Explicit model routing; bounded model specialists disabled by default |
| `RETRIEVAL_BACKEND`, `EMBEDDING_MODEL`, `RERANKER_MODEL`, `MODEL_CACHE_DIR` | Learned retrieval and local model cache |
| `ALLOWED_HOSTS` | Explicit accepted HTTP host names |
| `LLM_INPUT_COST_PER_MILLION`, `LLM_OUTPUT_COST_PER_MILLION` | Operator-supplied prices for estimated cost; zero means no price supplied |
| `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` | Optional LangGraph/LangChain tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Optional OTLP HTTP tracing exporter |
| `APPROVAL_THRESHOLD`, `REFUND_APPROVAL_THRESHOLD` | Risk/high-value and return review thresholds in INR |
| `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` | Optional private purchase-order archival |
| `CORS_ORIGINS` | JSON list of explicitly allowed frontend origins |

Production startup rejects demo secrets/seeding, SQLite, missing dependencies, wildcard hosts and non-HTTPS origins. Model-driven specialists require an explicit provider and key. This is a startup guard, not a production certification.


Defaults and validation: [backend/config.py](../backend/config.py). Restart processes after changing environment variables.
