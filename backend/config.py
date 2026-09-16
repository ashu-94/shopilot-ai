from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./data/shopilot.db"
    checkpoint_url: str = "./data/checkpoints.db"
    jwt_secret: str = "local-demo-only-change-this-32-character-secret"
    demo_password: str = "ShopPilot-demo-2026!"
    seed_demo: bool = True
    redis_url: str = ""
    qdrant_url: str = ""
    retrieval_backend: str = "lexical"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-12-v2"
    model_cache_dir: str = "./data/models"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver", "backend"]
    kafka_bootstrap_servers: str = ""
    mcp_transport: str = "inprocess"
    mcp_host: str = "mcp"
    llm_provider: str = "deterministic"
    specialist_models_enabled: bool = False
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_fast_model: str = "gpt-4.1-mini"
    llm_advanced_model: str = "gpt-4.1"
    llm_input_cost_per_million: float = 0
    llm_output_cost_per_million: float = 0
    approval_threshold: int = 100000
    refund_approval_threshold: int = 10000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    otel_exporter_otlp_endpoint: str = ""
    s3_endpoint_url: str = ""
    s3_bucket: str = "shopilot-documents"

    def validate_runtime(self) -> None:
        if self.specialist_models_enabled and (self.llm_provider == "deterministic" or not self.llm_api_key):
            raise ValueError("Model-driven specialists require an explicit provider and API key")
        if self.app_env == "production":
            if (
                any(word in self.jwt_secret.lower() for word in ["local-demo", "change-me", "replace_me"])
                or len(self.jwt_secret) < 32
            ):
                raise ValueError("Production requires a unique JWT_SECRET of at least 32 characters")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("Production requires an explicit allowed host list")
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production browser origins must use HTTPS")
            if (
                self.retrieval_backend != "learned"
                or not self.qdrant_url
                or not self.kafka_bootstrap_servers
                or not self.s3_endpoint_url
            ):
                raise ValueError("Production requires learned retrieval, Qdrant, Kafka and object storage")
            if (
                self.seed_demo
                or not self.redis_url
                or not self.database_url.startswith("postgresql")
                or not self.checkpoint_url.startswith("postgresql")
            ):
                raise ValueError("Production requires SEED_DEMO=false, Redis and PostgreSQL")


@lru_cache
def settings() -> Settings:
    return Settings()
