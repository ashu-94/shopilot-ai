"""Disposable API for browser/load tests; never uses the user's demo database."""

import os
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="shopilot-browser-"))
os.environ.update(
    DATABASE_URL="sqlite:///" + (root / "test.db").as_posix(),
    CHECKPOINT_URL=str(root / "checkpoints.db"),
    APP_ENV="development",
    SEED_DEMO="true",
    REDIS_URL="",
    QDRANT_URL="",
    KAFKA_BOOTSTRAP_SERVERS="",
    MCP_TRANSPORT="inprocess",
    RETRIEVAL_BACKEND="lexical",
    LLM_PROVIDER="deterministic",
    CORS_ORIGINS='["http://127.0.0.1:4173"]',
)
import uvicorn  # noqa: E402

from backend.db import Base, engine  # noqa: E402
from backend.seed import seed  # noqa: E402

Base.metadata.create_all(engine)
seed()
uvicorn.run("backend.main:app", host="127.0.0.1", port=8123, access_log=False)
