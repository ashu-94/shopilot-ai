"""Executable full-stack proof. Run inside the verification backend container."""

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import boto3
import httpx
import redis
from qdrant_client import QdrantClient
from sqlalchemy import func, select

from backend.config import settings
from backend.db import Session, engine
from backend.models import ConsumerReceipt, Order, OutboxEvent
from backend.semantic import collection_name

REPORT = Path("data/verification")
REPORT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30)


def request(path, method="GET", token=None, body=None):
    headers = {"Idempotency-Key": str(uuid4())}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.request(method, "/api" + path, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


def login(email="alex@shopilot.demo"):
    return request("/auth/login", "POST", body={"email": email, "password": settings().demo_password})[
        "access_token"
    ]


def wait(execution_id, token):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        result = request(f"/executions/{execution_id}", token=token)
        if result["status"] not in {"running", "queued"}:
            assert result["status"] != "failed", result
            return result
        time.sleep(0.5)
    raise AssertionError("Workflow timeout")


def prepare():
    token = login()
    request("/cart", "PUT", token, {"items": [{"product_id": "product-010", "quantity": 2}]})
    run = request("/checkout", "POST", token, {"address": "42 Demo Avenue, Bengaluru 560001"})
    pending = wait(run["id"], token)
    assert pending["status"] == "awaiting_approval"
    (REPORT / "restart.json").write_text(json.dumps({"execution_id": run["id"]}))
    return run["id"]


def resume():
    token = login()
    execution_id = json.loads((REPORT / "restart.json").read_text())["execution_id"]
    pending = wait(execution_id, token)
    if pending["status"] != "completed":
        approval = next(a for a in request("/approvals", token=token) if a["execution_id"] == execution_id)
        approver = login("manager@shopilot.demo") if approval["required_role"] == "MANAGER" else token
        request(f"/approvals/{approval['id']}/decision", "POST", approver, {"decision": "approve"})
    completed = wait(execution_id, token)
    assert completed["status"] == "completed"
    order_id = completed["result"]["order"]["id"]
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.idempotency_key == f"order:{execution_id}")
            )
            == 1
        )
    return order_id


def kafka_probe(outage=False):
    if outage:
        probe_id = uuid4().hex
        with Session.begin() as db:
            db.add(
                OutboxEvent(
                    id=probe_id,
                    type="verification.probe",
                    aggregate_id=probe_id,
                    payload={"schema_version": 1},
                )
            )
        (REPORT / "kafka.json").write_text(json.dumps({"event_id": probe_id}))
        time.sleep(3)
        with Session() as db:
            assert not db.get(OutboxEvent, probe_id).published, "Outbox unexpectedly drained during outage"
    else:
        probe_id = json.loads((REPORT / "kafka.json").read_text())["event_id"]
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            with Session() as db:
                if db.get(ConsumerReceipt, (probe_id, "analytics")):
                    return
            time.sleep(1)
        raise AssertionError("Kafka did not replay durable outbox after recovery")


def full_stack():
    config = settings()
    assert engine.dialect.name == "postgresql"
    assert config.kafka_bootstrap_servers and config.mcp_transport == "http"
    assert client.get("/health/ready").json()["database"] == "postgresql"
    cache = redis.Redis.from_url(config.redis_url)
    key = "verification:" + uuid4().hex
    cache.set(key, "ok", ex=60)
    assert cache.get(key) == b"ok"
    cache.delete(key)
    qdrant = QdrantClient(url=config.qdrant_url)
    assert qdrant.get_collection(collection_name()).points_count > 0
    token = login()
    mission = request(
        "/missions", "POST", token, {"query": "AI/ML laptop monitor chair keyboard mouse UPS under ₹150000"}
    )
    result = wait(mission["id"], token)
    assert len(result["result"]["products"]) == 6 and result["result"]["total"] <= 150000
    assert result["result"]["retrieval"]["vector_store_available"]
    assert result["result"]["retrieval"]["embedding_model"] == config.embedding_model
    prepare()
    order_id = resume()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        notices = request("/notifications", token=token)
        if any(n["order_id"] == order_id for n in notices):
            break
        time.sleep(1)
    else:
        raise AssertionError("Kafka-backed notification not delivered")
    storage = boto3.client("s3", endpoint_url=config.s3_endpoint_url)
    bucket = config.s3_bucket
    try:
        storage.head_bucket(Bucket=bucket)
    except storage.exceptions.ClientError as exc:
        if str(exc.response["Error"]["Code"]) not in {"404", "NoSuchBucket"}:
            raise
        storage.create_bucket(Bucket=bucket)
    key = "verification/" + uuid4().hex + ".json"
    storage.put_object(Bucket=bucket, Key=key, Body=b'{"proof":true}')
    assert storage.get_object(Bucket=bucket, Key=key)["Body"].read() == b'{"proof":true}'
    storage.delete_object(Bucket=bucket, Key=key)
    with httpx.Client(timeout=10) as monitoring:
        assert monitoring.get("http://grafana:3000/api/health").json()["database"] == "ok"
        assert monitoring.get("http://otel-collector:13133/").status_code == 200
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            query = monitoring.get(
                "http://prometheus:9090/api/v1/query", params={"query": 'up{job="shopilot"}'}
            ).json()
            if any(float(x["value"][1]) == 1 for x in query.get("data", {}).get("result", [])):
                break
            time.sleep(2)
        else:
            raise AssertionError("Prometheus did not scrape backend")
    return {
        "postgresql": True,
        "redis": True,
        "qdrant_learned_retrieval": True,
        "kafka_notifications": True,
        "minio_round_trip": True,
        "grafana": True,
        "prometheus_scrape": True,
        "otel_collector": True,
        "distributed_mcp": True,
        "approved_mock_checkout": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=["full", "prepare-restart", "resume", "kafka-outage", "kafka-recovery"],
        default="full",
    )
    args = parser.parse_args()
    result = (
        {
            "full": full_stack,
            "prepare-restart": prepare,
            "resume": resume,
            "kafka-outage": lambda: kafka_probe(True),
            "kafka-recovery": kafka_probe,
        }[args.phase]
    )()
    report = {"phase": args.phase, "passed": True, "result": result, "timestamp": time.time()}
    (REPORT / (args.phase + ".json")).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
