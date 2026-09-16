from sqlalchemy import func, select

from backend.db import Base, Session, engine
from backend.events import consume
from backend.models import ConsumerReceipt, uid


def test_duplicate_domain_event_is_consumed_once():
    Base.metadata.create_all(engine)
    event = {"id": uid(), "type": "order.created", "aggregate_id": uid(), "payload": {"schema_version": 1}}
    consume(event, "analytics")
    consume(event, "analytics")
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ConsumerReceipt)
                .where(ConsumerReceipt.event_id == event["id"])
            )
            == 1
        )
