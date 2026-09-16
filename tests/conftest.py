import os
import tempfile
from pathlib import Path

TEST_DIRECTORY = Path(tempfile.mkdtemp(prefix="shopilot-test-"))
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{(TEST_DIRECTORY / 'test.db').as_posix()}"
)
os.environ["CHECKPOINT_URL"] = os.environ.get("TEST_CHECKPOINT_URL", str(TEST_DIRECTORY / "checkpoints.db"))
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "")
os.environ["MCP_TRANSPORT"] = "inprocess"
os.environ["LLM_PROVIDER"] = "deterministic"
