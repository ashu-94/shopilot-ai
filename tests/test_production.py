from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend import commerce, events, tools
from backend.db import Base, Session, engine
from backend.errors import DomainError
from backend.main import app
from backend.models import (
    AgentExecution,
    Approval,
    DomainProjection,
    Notification,
    Order,
    OutboxEvent,
    Payment,
    Refund,
    ReturnItem,
    User,
    uid,
)
from backend.policies import fingerprint
from backend.review_analysis import analyze
from backend.seed import seed
from tests.test_commerce import approved_checkout


def procurement_details():
    return {
        "organization": "Example Engineering",
        "cost_center": "ENG-42",
        "delivery_address": "42 Business Avenue, Bengaluru 560001",
        "billing_address": "42 Accounts Avenue, Bengaluru 560001",
        "contact_email": "buyer@example.test",
        "requested_delivery_date": str(date.today() + timedelta(days=30)),
        "reference": "REQ-42",
        "payment_terms": "prepaid_mock",
    }


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(engine)
    seed()


def customer():
    with Session() as db:
        return db.scalar(select(User).where(User.role == "CUSTOMER"))


def approve_return(user, order, quantity):
    items = [{"product_id": order["items"][0]["product_id"], "quantity": quantity}]
    payload = {
        "order_id": order["id"],
        "items": items,
        "quote": commerce.return_quote(user.id, order["id"], items),
        "return_id": uid(),
        "resolution": "refund",
        "reason": "The item arrived damaged",
    }
    with Session.begin() as db:
        execution = AgentExecution(
            user_id=user.id, kind="return", query="Return damaged item", payload=payload
        )
        db.add(execution)
        db.flush()
        db.add(
            Approval(
                execution_id=execution.id,
                user_id=user.id,
                amount=payload["quote"]["total"],
                reason="Reviewed",
                risk_score=0,
                required_role="OWNER",
                status="approved",
                request_hash=fingerprint(payload),
            )
        )
        return execution.id


def test_partial_refund_rounding_and_replay():
    user = customer()
    order = commerce.create_order(user.id, approved_checkout(user.id, quantity=3))
    # Force a one-rupee allocation remainder to exercise cumulative rounding.
    with Session.begin() as db:
        row = db.get(Order, order["id"])
        row.total -= 1
        row.discount += 1
        db.scalar(select(Payment).where(Payment.order_id == row.id)).amount = row.total
        total = row.total
    amounts = []
    for _ in range(3):
        execution = approve_return(user, order, 1)
        result = commerce.resolve_return(user.id, execution)
        assert commerce.resolve_return(user.id, execution) == result
        amounts.append(result["amount"])
    assert sum(amounts) == total
    with Session() as db:
        assert db.get(Order, order["id"]).status == "refunded"
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReturnItem)
                .join(commerce.Return)
                .where(commerce.Return.order_id == order["id"])
            )
            == 3
        )
    with pytest.raises(DomainError):
        commerce.return_quote(user.id, order["id"])


def test_two_return_requests_cannot_refund_same_unit():
    user = customer()
    order = commerce.create_order(user.id, approved_checkout(user.id))
    executions = [approve_return(user, order, 1) for _ in range(2)]

    def resolve(execution):
        try:
            return commerce.resolve_return(user.id, execution)
        except DomainError:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(resolve, executions))
    assert sum(r is not None for r in results) == 1
    with Session() as db:
        assert (
            db.scalar(select(func.sum(Refund.amount)).where(Refund.order_id == order["id"])) == order["total"]
        )


def test_foreign_product_return_rejected():
    user = customer()
    order = commerce.create_order(user.id, approved_checkout(user.id))
    with pytest.raises(DomainError):
        commerce.return_quote(user.id, order["id"], [{"product_id": "product-001", "quantity": 1}])


def test_event_projections_and_notifications_are_idempotent():
    user = customer()
    order = commerce.create_order(user.id, approved_checkout(user.id))
    event = {
        "id": uid(),
        "type": "order.created",
        "aggregate_id": order["id"],
        "payload": {"schema_version": 1},
    }
    for name in events.CONSUMERS:
        events.consume(event, name)
        events.consume(event, name)
    with Session() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Notification).where(Notification.event_id == event["id"])
            )
            == 1
        )
        assert (
            db.get(DomainProjection, (order["id"], "payment-projection")).data["payment"]["status"]
            == "completed"
        )


async def test_specialist_cannot_impersonate_order_agent():
    token = tools.active_agent.set("search")
    try:
        with pytest.raises(DomainError, match="impersonate"):
            await tools.call("order", customer().id, "create_order", execution_id=uid())
    finally:
        tools.active_agent.reset(token)


def test_review_quality_reports_evidence_and_uncertainty():
    result = analyze(
        [
            {"id": "1", "text": "Quiet fan and fast performance", "rating": 5, "verified": True},
            {"id": "2", "text": "Quiet fan and fast performance", "rating": 5, "verified": False},
            {"id": "3", "text": "Battery broke quickly", "rating": 1, "verified": True},
        ]
    )
    assert result["duplicate_text_count"] == 1
    assert result["aspects"]["battery"]["average_rating"] == 1
    assert result["confidence"] == "low"


def test_request_security_boundaries():
    with TestClient(app) as client:
        assert client.post("/api/auth/refresh", headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/auth/login", content=b"x" * 65537).status_code == 413
        assert client.get("/api/products", headers={"Host": "evil.example"}).status_code == 400
        assert client.post("/api/auth/login", content="{").status_code == 400
        assert client.get("/api/config").headers["cache-control"] == "no-store"
        assert client.get("/api/admin/recovery").status_code == 401


def test_recovery_is_admin_only_and_audited():
    with TestClient(app) as client:

        def login(email):
            result = client.post("/api/auth/login", json={"email": email, "password": "ShopPilot-demo-2026!"})
            return {"Authorization": "Bearer " + result.json()["access_token"]}

        user_headers = login("alex@shopilot.demo")
        assert client.get("/api/admin/recovery", headers=user_headers).status_code == 403
        admin_headers = login("admin@shopilot.demo")
        with Session.begin() as db:
            event = OutboxEvent(
                type="test.retry", aggregate_id=uid(), payload={"schema_version": 1}, attempts=8
            )
            db.add(event)
            db.flush()
            event_id = event.id
        result = client.post(
            f"/api/admin/outbox/{event_id}/replay",
            headers=admin_headers,
            json={"reason": "Broker repaired and connectivity checked"},
        )
        assert result.status_code == 200
        assert client.get("/api/admin/recovery", headers=admin_headers).status_code == 200


async def test_independent_model_loop_uses_only_scoped_read_tools(monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    from backend import agent_models
    from backend.config import settings

    class ToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    fake = ToolModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_products",
                        "args": {"category": "laptop", "max_price": 100000},
                        "id": "inspection-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Catalog candidates inspected."),
        ]
    )
    monkeypatch.setattr(agent_models, "ChatOpenAI", lambda **kwargs: fake)
    monkeypatch.setattr(settings(), "specialist_models_enabled", True)
    monkeypatch.setattr(settings(), "llm_provider", "compatible")
    monkeypatch.setattr(settings(), "llm_api_key", "local-test-key")
    token = tools.active_agent.set("search")
    try:
        result = await agent_models.inspect_evidence(
            "search",
            "Inspect laptop candidates",
            {"user_id": customer().id, "user_query": "Laptop under 100000", "kind": "shopping"},
        )
        assert result["mode"] == "model_tool_loop" and result["tool_calls"] == 1
        for agent in tools.PERMISSIONS:
            names = {tool.name for tool in agent_models.bound_tools(agent, customer().id)}
            assert names <= tools.PERMISSIONS[agent]
            assert not names & {
                "create_order",
                "refund_payment",
                "create_payment",
                "cancel_order",
                "reserve_inventory",
            }
    finally:
        tools.active_agent.reset(token)
