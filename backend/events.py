import asyncio
import json
import logging
import time

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.commerce import order_data
from backend.config import settings
from backend.db import Session
from backend.models import (
    AuditLog,
    ConsumerReceipt,
    DeadLetter,
    DomainProjection,
    Notification,
    Order,
    OutboxEvent,
)
from backend.observability import EVENTS
from backend.repositories import required

log = logging.getLogger(__name__)
CONSUMERS = ["inventory-projection", "payment-projection", "notification", "analytics", "audit"]


def consume(event: dict, consumer: str):
    try:
        with Session.begin() as db:
            if db.get(ConsumerReceipt, (event["id"], consumer)):
                return
            db.add(ConsumerReceipt(event_id=event["id"], consumer=consumer))
            db.flush()
            order = db.scalar(select(Order).where(Order.id == event["aggregate_id"]).with_for_update())
            if order:
                snapshot = order_data(db, order)
                if consumer == "notification":
                    db.add(
                        Notification(
                            user_id=order.user_id,
                            order_id=order.id,
                            event_id=event["id"],
                            message=f"Order {snapshot['number']}: {event['type'].replace('.', ' ')}",
                        )
                    )
                elif consumer in {"inventory-projection", "payment-projection", "analytics"}:
                    data = (
                        {
                            "items": [
                                {"product_id": i["product_id"], "available": i["product"]["stock"]}
                                for i in snapshot["items"]
                            ]
                        }
                        if consumer == "inventory-projection"
                        else {"payment": snapshot["payment"], "total": snapshot["total"]}
                        if consumer == "payment-projection"
                        else {
                            "status": snapshot["status"],
                            "total": snapshot["total"],
                            "kind": snapshot["kind"],
                        }
                    )
                    projection = db.get(DomainProjection, (order.id, consumer))
                    if projection:
                        projection.data, projection.updated_at = data, time.time()
                    else:
                        db.add(DomainProjection(aggregate_id=order.id, consumer=consumer, data=data))
            # Notifications stay inside the authenticated application.
            db.add(
                AuditLog(
                    action=f"event.{consumer}",
                    resource_id=event["aggregate_id"],
                    detail={"event_id": event["id"], "type": event["type"]},
                )
            )
        EVENTS.labels(event["type"], "consumed").inc()
    except IntegrityError:
        with Session() as db:
            if not db.get(ConsumerReceipt, (event["id"], consumer)):
                raise  # A real projection failure must retry, not be silently acknowledged.


async def relay_once(producer=None):
    with Session() as db:
        events = db.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.published.is_(False),
                OutboxEvent.next_attempt_at <= time.time(),
                OutboxEvent.attempts < 8,
            )
            .order_by(OutboxEvent.created_at)
            .limit(50)
        ).all()
    for row in events:
        envelope = {"id": row.id, "type": row.type, "aggregate_id": row.aggregate_id, "payload": row.payload}
        try:
            if producer:
                await producer.send_and_wait(
                    "shopilot.domain", json.dumps(envelope).encode(), key=row.aggregate_id.encode()
                )
            else:
                for consumer in CONSUMERS:
                    await asyncio.to_thread(consume, envelope, consumer)
            with Session.begin() as db:
                required(db, OutboxEvent, row.id).published = True
            EVENTS.labels(row.type, "published").inc()
        except Exception as exc:
            with Session.begin() as db:
                item = required(db, OutboxEvent, row.id)
                item.attempts += 1
                item.error = type(exc).__name__
                item.next_attempt_at = time.time() + min(300, 2**item.attempts)
            EVENTS.labels(row.type, "retry").inc()


async def relay_loop():
    producer = None
    try:
        while True:
            try:
                if settings().kafka_bootstrap_servers and not producer:
                    producer = AIOKafkaProducer(
                        bootstrap_servers=settings().kafka_bootstrap_servers,
                        enable_idempotence=True,
                        request_timeout_ms=10000,
                    )
                    await producer.start()
                await relay_once(producer)
            except Exception:
                log.warning("Kafka relay unavailable; events remain in the transactional outbox")
                if producer:
                    await producer.stop()
                    producer = None
                await asyncio.sleep(5)
            await asyncio.sleep(1)
    finally:
        if producer:
            await producer.stop()


async def consume_loop():
    if not settings().kafka_bootstrap_servers:
        return
    while True:
        consumer = AIOKafkaConsumer(
            "shopilot.domain",
            bootstrap_servers=settings().kafka_bootstrap_servers,
            group_id="shopilot-projections-v1",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
            async for message in consumer:
                try:
                    envelope = json.loads(message.value)
                    validate_envelope(envelope)
                    for name in CONSUMERS:
                        await asyncio.to_thread(consume, envelope, name)
                except (ValueError, KeyError, TypeError):
                    with Session.begin() as db:
                        source_key = f"{message.topic}:{message.partition}:{message.offset}"
                        if not db.scalar(select(DeadLetter).where(DeadLetter.source_key == source_key)):
                            db.add(
                                DeadLetter(
                                    source_key=source_key,
                                    envelope={"raw": message.value.decode("utf-8", errors="replace")[:10000]},
                                    reason="Invalid event schema",
                                )
                            )
                        db.add(
                            AuditLog(
                                action="event.dead_letter",
                                resource_id=str(message.offset),
                                detail={
                                    "topic": message.topic,
                                    "partition": message.partition,
                                    "reason": "Invalid event schema",
                                },
                            )
                        )
                await consumer.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("Kafka consumer reconnecting; uncommitted messages will replay")
            await asyncio.sleep(5)
        finally:
            await consumer.stop()


def validate_envelope(event):
    if not isinstance(event, dict) or not all(
        isinstance(event.get(k), str) and 0 < len(event[k]) <= 80 for k in ["id", "type", "aggregate_id"]
    ):
        raise ValueError("Invalid event identity")
    if not isinstance(event.get("payload"), dict) or event["payload"].get("schema_version") != 1:
        raise ValueError("Unsupported event schema")
