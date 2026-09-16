"""Add workflow request idempotency keys for existing development databases."""

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    if "request_key" not in {c["name"] for c in inspect(op.get_bind()).get_columns("agent_executions")}:
        with op.batch_alter_table("agent_executions") as batch:
            batch.add_column(Column("request_key", String(180), nullable=True))
            batch.create_unique_constraint("uq_execution_request_key", ["request_key"])


def downgrade():
    with op.batch_alter_table("agent_executions") as batch:
        batch.drop_column("request_key")
