import os
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect


def test_migrations_upgrade_downgrade_and_upgrade():
    tmp_path = Path(tempfile.mkdtemp(prefix="shopilot-migration-"))
    database = tmp_path / "migrated.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}"}
    for revision in ["head", "base", "head"]:
        command = "downgrade" if revision == "base" else "upgrade"
        result = subprocess.run(
            [sys.executable, "-m", "alembic", command, revision], env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
    connection = create_engine(env["DATABASE_URL"])
    names = inspect(connection).get_table_names()
    assert "orders" in names and "agent_executions" in names and "approvals" in names
    connection.dispose()
