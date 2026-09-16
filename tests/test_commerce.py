from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, update

from backend.commerce import create_order, quote
from backend.db import Base, Session, engine
from backend.errors import DomainError
from backend.models import AgentExecution, Approval, Inventory, Order, Payment, User
from backend.policies import fingerprint
from backend.seed import seed


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(engine)
    seed()


def approved_checkout(user_id, product_id="product-010", quantity=1, fail=False):
    with Session.begin() as db:
        items = [{"product_id": product_id, "quantity": quantity}]
        payload = {
            "items": items,
            "quote": quote(db, items),
            "address": "42 Demo Avenue, Test City",
            "simulate_failure": fail,
        }
        execution = AgentExecution(user_id=user_id, kind="checkout", query="checkout", payload=payload)
        db.add(execution)
        db.flush()
        db.add(
            Approval(
                execution_id=execution.id,
                user_id=user_id,
                amount=payload["quote"]["total"],
                reason="Test confirmation",
                risk_score=0,
                required_role="OWNER",
                status="approved",
                decided_by=user_id,
                request_hash=fingerprint(payload),
            )
        )
        return execution.id


def test_idempotent_order_and_payment():
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
    execution = approved_checkout(user.id)
    first = create_order(user.id, execution)
    assert create_order(user.id, execution)["id"] == first["id"]
    with Session() as db:
        assert (
            db.scalar(select(func.count()).select_from(Payment).where(Payment.order_id == first["id"])) == 1
        )


def test_two_purchases_do_not_oversell():
    with Session.begin() as db:
        users = db.scalars(select(User).limit(2)).all()
        db.execute(update(Inventory).where(Inventory.product_id == "product-011").values(available=1))
    executions = [approved_checkout(u.id, "product-011") for u in users]

    def buy(pair):
        try:
            return create_order(pair[0].id, pair[1])["id"]
        except DomainError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(buy, zip(users, executions)))
    assert len([r for r in results if r]) == 1
    with Session.begin() as db:
        assert db.get(Inventory, "product-011").available == 0
        db.execute(update(Inventory).where(Inventory.product_id == "product-011").values(available=120))


def test_failed_payment_rolls_back_stock_and_order():
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
        before = db.get(Inventory, "product-010").available
    execution = approved_checkout(user.id, fail=True)
    with pytest.raises(DomainError, match="declined"):
        create_order(user.id, execution)
    with Session() as db:
        assert db.get(Inventory, "product-010").available == before
        assert db.scalar(select(Order).where(Order.idempotency_key == f"order:{execution}")) is None


def test_approval_tamper_blocked():
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
    execution = approved_checkout(user.id)
    with Session.begin() as db:
        row = db.get(AgentExecution, execution)
        row.payload = {**row.payload, "address": "Changed after confirmation"}
    with pytest.raises(DomainError, match="changed"):
        create_order(user.id, execution)
