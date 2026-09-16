import pytest
from sqlalchemy import select

from backend.db import Base, Session, engine
from backend.models import AgentExecution, Approval, User
from backend.seed import seed
from backend.workflows import WorkflowRunner, create_execution, decide
from tests.test_commerce import approved_checkout


@pytest.fixture(autouse=True)
def setup():
    Base.metadata.create_all(engine)
    seed()


async def test_shopping_workflow():
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
    row = create_execution(
        user.id, "shopping", "AI/ML home office laptop monitor chair keyboard mouse UPS under ₹150000", {}
    )
    runner = WorkflowRunner()
    await runner.open()
    try:
        await runner.execute(row["id"])
        with Session() as db:
            result = db.get(AgentExecution, row["id"])
            assert result.status == "completed", result.error
            assert len(result.result["products"]) == 6
            assert result.result["total"] <= 150000
    finally:
        await runner.close()


async def test_approval_survives_runner_restart():
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
    execution_id = approved_checkout(user.id)
    with Session.begin() as db:
        approval = db.scalar(select(Approval).where(Approval.execution_id == execution_id))
        approval.status = "pending"
        approval_id = approval.id
    first = WorkflowRunner()
    await first.open()
    await first.execute(execution_id)
    await first.close()
    with Session() as db:
        assert db.get(AgentExecution, execution_id).status == "awaiting_approval"
    decide(user, approval_id, "approve", "Reviewed the exact quote")
    restarted = WorkflowRunner()
    await restarted.open()
    await restarted.execute(execution_id)
    await restarted.close()
    with Session() as db:
        result = db.get(AgentExecution, execution_id)
        assert result.status == "completed", result.error
        assert result.result["order"]["payment"]["provider"] == "safe_mock"
