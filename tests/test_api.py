import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import Base, Session, engine
from backend.main import app
from backend.models import Approval, Inventory, User
from backend.seed import seed
from backend.workflows import WorkflowRunner, create_execution, decide
from tests.test_production import procurement_details


@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    seed()
    with TestClient(app) as client:
        yield client


def sign_in(client, email="alex@shopilot.demo"):
    response = client.post("/api/auth/login", json={"email": email, "password": "ShopPilot-demo-2026!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def wait_for(client, execution_id, headers):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = client.get(f"/api/executions/{execution_id}", headers=headers)
        assert response.status_code == 200, response.text
        row = response.json()
        if row["status"] not in {"queued", "running"}:
            return row
        time.sleep(0.1)
    raise AssertionError("Workflow did not finish before deadline")


def test_api_shopping_checkout_and_sse(client):
    headers = sign_in(client)
    response = client.post(
        "/api/missions",
        headers=headers,
        json={"query": "AI/ML home office laptop monitor chair keyboard mouse UPS under ₹150000"},
    )
    assert response.status_code == 202
    mission = wait_for(client, response.json()["id"], headers)
    assert mission["status"] == "completed", mission
    items = [{"product_id": p["id"], "quantity": 1} for p in mission["result"]["products"]]
    assert client.put("/api/cart", headers=headers, json={"items": items}).status_code == 200
    key = str(uuid.uuid4())
    checkout_headers = {**headers, "Idempotency-Key": key}
    payload = {"address": "42 Demo Avenue, Bengaluru 560001"}
    checkout = client.post("/api/checkout", headers=checkout_headers, json=payload)
    assert checkout.status_code == 202, checkout.text
    assert (
        client.post("/api/checkout", headers=checkout_headers, json=payload).json()["id"]
        == checkout.json()["id"]
    )
    changed = client.post(
        "/api/checkout", headers=checkout_headers, json={"address": "A completely different demo address"}
    )
    assert changed.status_code == 409
    execution = wait_for(client, checkout.json()["id"], headers)
    assert execution["status"] == "awaiting_approval", execution
    approval = next(
        a
        for a in client.get("/api/approvals", headers=headers).json()
        if a["execution_id"] == execution["id"]
    )
    assert (
        client.post(
            f"/api/approvals/{approval['id']}/decision", headers=headers, json={"decision": "approve"}
        ).status_code
        == 200
    )
    result = wait_for(client, execution["id"], headers)
    assert result["status"] == "completed", result
    assert result["result"]["order"]["payment"]["status"] == "completed"
    assert client.get("/api/cart", headers=headers).json()["items"] == []
    assert (
        client.post("/api/checkout", headers=checkout_headers, json=payload).json()["id"] == execution["id"]
    )
    stream = client.get(f"/api/executions/{execution['id']}/events", headers=headers)
    assert stream.status_code == 200 and "event: done" in stream.text
    assert "chain-of-thought" not in stream.text


def test_auth_rotation_and_rbac(client):
    customer = sign_in(client)
    old_cookie = client.cookies.get("shopilot_refresh")
    assert client.get("/api/admin", headers=customer).status_code == 403
    assert client.get("/api/orders").status_code == 401
    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    assert client.cookies.get("shopilot_refresh") != old_cookie
    replay = client.post("/api/auth/refresh", headers={"Cookie": f"shopilot_refresh={old_cookie}"})
    assert replay.status_code == 401


def test_cross_account_workflow_access_denied(client):
    customer = sign_in(client)
    execution = client.post("/api/missions", headers=customer, json={"query": "laptop under ₹100000"}).json()
    other = sign_in(client, "business@shopilot.demo")
    assert client.get(f"/api/executions/{execution['id']}", headers=other).status_code == 404
    assert client.get(f"/api/executions/{execution['id']}/events", headers=other).status_code == 404
    denied = client.post(
        "/api/missions", headers=customer, json={"query": "20 laptops under ₹2500000", "mode": "procurement"}
    )
    assert denied.status_code == 403


async def test_procurement_requires_independent_manager():
    Base.metadata.create_all(engine)
    seed()
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "BUSINESS_USER"))
        manager = db.scalar(select(User).where(User.role == "MANAGER"))
    row = create_execution(
        user.id,
        "procurement",
        "20 laptops 32GB RAM 1TB SSD three-year warranty budget ₹25 lakh",
        {"procurement": procurement_details()},
    )
    runner = WorkflowRunner()
    await runner.open()
    await runner.execute(row["id"])
    with Session() as db:
        approval = db.scalar(select(Approval).where(Approval.execution_id == row["id"]))
        assert approval.required_role == "MANAGER"
    from backend.errors import DomainError

    with pytest.raises(DomainError):
        decide(user, approval.id, "approve", "Self approval")
    decide(manager, approval.id, "request_info", "Please confirm the team allocation")
    decide(manager, approval.id, "reject", "Use a smaller batch for this test")
    await runner.execute(row["id"])
    await runner.close()
    from backend.models import AgentExecution

    with Session() as db:
        assert db.get(AgentExecution, row["id"]).status == "rejected"


def test_invalid_cart_quantities_and_unknown_brands(client):
    headers = sign_in(client)
    assert (
        client.put(
            "/api/cart", headers=headers, json={"items": [{"product_id": "product-001", "quantity": -1}]}
        ).status_code
        == 422
    )
    response = client.post(
        "/api/missions", headers=headers, json={"query": "Show current MacBook Pro prices"}
    )
    result = wait_for(client, response.json()["id"], headers)
    assert result["status"] == "failed" and "fictional" in result["error"]


def test_return_refund_and_duplicate_prevention(client):
    from backend.commerce import create_order
    from tests.test_commerce import approved_checkout

    headers = sign_in(client)
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
    order = create_order(user.id, approved_checkout(user.id))
    body = {
        "order_id": order["id"],
        "reason": "The mouse arrived with damage to the shell",
        "resolution": "refund",
    }
    response = client.post(
        "/api/returns", headers={**headers, "Idempotency-Key": str(uuid.uuid4())}, json=body
    )
    assert response.status_code == 202, response.text
    execution = wait_for(client, response.json()["id"], headers)
    approval = next(
        a
        for a in client.get("/api/approvals", headers=headers).json()
        if a["execution_id"] == execution["id"]
    )
    assert (
        client.post(
            f"/api/approvals/{approval['id']}/decision", headers=headers, json={"decision": "approve"}
        ).status_code
        == 200
    )
    result = wait_for(client, execution["id"], headers)
    assert result["status"] == "completed", result
    assert result["result"]["return"]["resolution"] == "refund"
    assert (
        client.post(
            "/api/returns", headers={**headers, "Idempotency-Key": str(uuid.uuid4())}, json=body
        ).status_code
        == 409
    )


def test_manager_approved_replacement(client):
    from backend.commerce import create_order
    from tests.test_commerce import approved_checkout

    headers = sign_in(client)
    with Session() as db:
        user = db.scalar(select(User).where(User.role == "CUSTOMER"))
    order = create_order(user.id, approved_checkout(user.id, "product-006"))
    with Session() as db:
        before = db.get(Inventory, "product-006").available
    response = client.post(
        "/api/returns",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={
            "order_id": order["id"],
            "reason": "The office chair arrived damaged",
            "resolution": "replacement",
        },
    )
    execution = wait_for(client, response.json()["id"], headers)
    approval = next(
        a
        for a in client.get("/api/approvals", headers=headers).json()
        if a["execution_id"] == execution["id"]
    )
    assert approval["required_role"] == "MANAGER"
    assert (
        client.post(
            f"/api/approvals/{approval['id']}/decision", headers=headers, json={"decision": "approve"}
        ).status_code
        == 403
    )
    manager = sign_in(client, "manager@shopilot.demo")
    assert (
        client.post(
            f"/api/approvals/{approval['id']}/decision", headers=manager, json={"decision": "approve"}
        ).status_code
        == 200
    )
    result = wait_for(client, execution["id"], headers)
    assert result["status"] == "completed", result
    with Session() as db:
        assert db.get(Inventory, "product-006").available == before - 1


def test_approved_procurement_generates_purchase_order(client):
    business = sign_in(client, "business@shopilot.demo")
    response = client.post(
        "/api/missions",
        headers=business,
        json={
            "query": "20 laptops for our engineering team with 32GB RAM 1TB SSD three-year warranty under ₹25 lakh",
            "mode": "procurement",
            "procurement": procurement_details(),
        },
    )
    assert response.status_code == 202, response.text
    execution = wait_for(client, response.json()["id"], business)
    assert execution["status"] == "awaiting_approval", execution
    manager = sign_in(client, "manager@shopilot.demo")
    approval = next(
        a
        for a in client.get("/api/approvals", headers=manager).json()
        if a["execution_id"] == execution["id"]
    )
    assert (
        client.post(
            f"/api/approvals/{approval['id']}/decision", headers=manager, json={"decision": "approve"}
        ).status_code
        == 200
    )
    completed = wait_for(client, execution["id"], business)
    assert completed["status"] == "completed", completed
    order = completed["result"]["order"]
    assert order["items"][0]["quantity"] == 20
    document = client.get(f"/api/orders/{order['id']}/purchase-order", headers=business)
    assert document.status_code == 200
    assert document.json()["number"].startswith("PO-")
    assert document.json()["total"] <= 2500000
    assert client.get(f"/api/orders/{order['id']}", headers=manager).status_code == 404
