import time

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.cache import cache
from backend.catalog import coupon_for, serialize_product
from backend.db import Session
from backend.errors import DomainError
from backend.models import (
    AgentExecution,
    Approval,
    AuditLog,
    Cart,
    CartItem,
    Inventory,
    Order,
    OrderItem,
    OutboxEvent,
    Payment,
    Product,
    Refund,
    Return,
    ReturnItem,
    Shipment,
    User,
    uid,
)
from backend.policies import fingerprint
from backend.repositories import required
from backend.schemas import CartInput


def emit(db, event_type: str, aggregate_id: str, payload: dict):
    db.add(
        OutboxEvent(
            type=event_type,
            aggregate_id=aggregate_id,
            payload={"schema_version": 1, "occurred_at": time.time(), **payload},
        )
    )


def owned_order(db, order_id: str, user_id: str) -> Order:
    order = db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise DomainError("Order not found.", 404)
    return order


def quote(db, items: list[dict], code: str | None = None) -> dict:
    validated = CartInput.model_validate({"items": items})
    if not validated.items:
        raise DomainError("Your cart is empty.")
    quantities: dict[str, int] = {}
    for item in validated.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
        if quantities[item.product_id] > 100:
            raise DomainError("Maximum 100 units per product.")
    lines: list[dict] = []
    for pid, quantity in sorted(quantities.items()):
        product, stock = required(db, Product, pid), required(db, Inventory, pid)
        if not product or not stock or stock.available < quantity:
            raise DomainError("A selected product has insufficient stock.", 409, "out_of_stock")
        lines.append(
            {
                "product_id": pid,
                "quantity": quantity,
                "unit_price": product.price,
                "product": serialize_product(product, stock.available),
            }
        )
    subtotal = sum(item["unit_price"] * item["quantity"] for item in lines)
    coupon = coupon_for(db, subtotal, code)
    return {
        "items": lines,
        "subtotal": subtotal,
        "discount": coupon["discount"],
        "coupon": coupon["code"],
        "shipping": 0,
        "total": subtotal - coupon["discount"],
        "currency": "INR",
        "delivery_days": max(item["product"]["delivery_days"] for item in lines),
    }


def cart(user_id: str) -> dict:
    with Session() as db:
        row = db.scalar(select(Cart).where(Cart.user_id == user_id))
        assert row is not None
        items = db.scalars(select(CartItem).where(CartItem.cart_id == row.id)).all()
        result: dict = (
            quote(db, [{"product_id": i.product_id, "quantity": i.quantity} for i in items])
            if items
            else {"items": [], "subtotal": 0, "discount": 0, "total": 0, "shipping": 0, "currency": "INR"}
        )
    cache.set(
        f"cart:{user_id}",
        {"items": [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in result["items"]]},
        3600,
    )
    return result


def set_cart(user_id: str, items: list[dict]) -> dict:
    with Session.begin() as db:
        lines = quote(db, items)["items"] if items else []
        row = db.scalar(select(Cart).where(Cart.user_id == user_id).with_for_update())
        assert row is not None
        db.execute(delete(CartItem).where(CartItem.cart_id == row.id))
        db.add_all(
            [CartItem(cart_id=row.id, product_id=i["product_id"], quantity=i["quantity"]) for i in lines]
        )
    cache.invalidate(f"cart:{user_id}")
    return cart(user_id)


def order_data(db, order: Order) -> dict:
    lines = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    payments = db.scalar(select(Payment).where(Payment.order_id == order.id))
    shipments = db.scalars(select(Shipment).where(Shipment.order_id == order.id)).all()
    return {
        "id": order.id,
        "number": f"SP-{order.id[:8].upper()}",
        "user_id": order.user_id,
        "status": order.status,
        "total": order.total,
        "discount": order.discount,
        "kind": order.kind,
        "created_at": order.created_at,
        "address": order.address,
        "procurement": order.procurement,
        "items": [
            {
                "product_id": i.product_id,
                "quantity": i.quantity,
                "returnable_quantity": i.quantity - i.returned_quantity,
                "unit_price": i.unit_price,
                "product": serialize_product(
                    required(db, Product, i.product_id), required(db, Inventory, i.product_id).available
                ),
            }
            for i in lines
        ],
        "payment": {"status": payments.status, "provider": payments.provider, "reference": payments.reference}
        if payments
        else None,
        "shipments": [
            {
                "tracking_code": s.tracking_code,
                "status": s.status,
                "estimated_days": s.estimated_days,
                "kind": s.kind,
            }
            for s in shipments
        ],
    }


def get_order(user_id: str, order_id: str) -> dict:
    with Session() as db:
        return order_data(db, owned_order(db, order_id, user_id))


def history(user_id: str) -> list[dict]:
    with Session() as db:
        return [
            order_data(db, o)
            for o in db.scalars(
                select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
            ).all()
        ]


def require_approval(db, execution_id: str, user_id: str) -> AgentExecution:
    execution = required(db, AgentExecution, execution_id)
    approval = db.scalar(select(Approval).where(Approval.execution_id == execution_id))
    if not execution or execution.user_id != user_id or not approval or approval.status != "approved":
        raise DomainError("A confirmed approval is required.", 403, "approval_required")
    if approval.request_hash != fingerprint(execution.payload):
        raise DomainError("The approved request changed. Create a new checkout.", 409)
    return execution


def create_order(user_id: str, execution_id: str) -> dict:
    key = f"order:{execution_id}"
    with cache.lock(key):
        try:
            with Session.begin() as db:
                execution = require_approval(db, execution_id, user_id)
                existing = db.scalar(select(Order).where(Order.idempotency_key == key))
                if existing:
                    return order_data(db, existing)
                payload = execution.payload
                current = quote(db, payload["items"])
                if current["total"] != payload["quote"]["total"] or any(
                    a["unit_price"] != b["unit_price"]
                    for a, b in zip(current["items"], payload["quote"]["items"], strict=True)
                ):
                    raise DomainError("Prices changed. Review a new checkout quote.", 409, "quote_changed")
                if payload.get("simulate_failure"):
                    raise DomainError(
                        "The mock payment was declined. No inventory was consumed.", 402, "payment_failed"
                    )
                for item in current["items"]:
                    mutation = db.execute(
                        update(Inventory)
                        .where(
                            Inventory.product_id == item["product_id"],
                            Inventory.available >= item["quantity"],
                        )
                        .values(
                            available=Inventory.available - item["quantity"], version=Inventory.version + 1
                        )
                    )
                    if getattr(mutation, "rowcount", 0) != 1:
                        raise DomainError(
                            "Inventory changed. Please review your cart.", 409, "inventory_race"
                        )
                order = Order(
                    user_id=user_id,
                    total=current["total"],
                    discount=current["discount"],
                    status="confirmed",
                    address=payload["address"],
                    kind=execution.kind,
                    idempotency_key=key,
                    request_hash=fingerprint(payload),
                    procurement=payload.get("procurement", {}),
                )
                db.add(order)
                db.flush()
                db.add_all(
                    [
                        OrderItem(
                            order_id=order.id,
                            product_id=i["product_id"],
                            quantity=i["quantity"],
                            unit_price=i["unit_price"],
                        )
                        for i in current["items"]
                    ]
                )
                db.add(
                    Payment(
                        order_id=order.id, amount=order.total, status="completed", reference=f"MOCK-{uid()}"
                    )
                )
                db.add(
                    Shipment(
                        order_id=order.id,
                        tracking_code=f"DEMO-{order.id[:12].upper()}",
                        estimated_days=current["delivery_days"],
                    )
                )
                for topic in ["order.created", "inventory.reserved", "payment.completed", "shipment.created"]:
                    emit(db, topic, order.id, {"order_id": order.id, "amount": order.total})
                db.add(
                    AuditLog(
                        user_id=user_id,
                        action="checkout.completed",
                        resource_id=order.id,
                        detail={"execution_id": execution_id, "provider": "safe_mock"},
                    )
                )
                if execution.kind == "checkout":
                    active_cart = db.scalar(select(Cart).where(Cart.user_id == user_id).with_for_update())
                    if active_cart:
                        for purchased in current["items"]:
                            cart_item = db.scalar(
                                select(CartItem).where(
                                    CartItem.cart_id == active_cart.id,
                                    CartItem.product_id == purchased["product_id"],
                                )
                            )
                            if cart_item:
                                remaining = cart_item.quantity - purchased["quantity"]
                                if remaining <= 0:
                                    db.delete(cart_item)
                                else:
                                    cart_item.quantity = remaining
                db.flush()
                result = order_data(db, order)
            cache.set(f"idempotency:{key}", {"order_id": result["id"]}, 86400)
            cache.invalidate(*(f"product:{i['product_id']}" for i in current["items"]), f"cart:{user_id}")
            return result
        except IntegrityError:
            with Session() as db:
                existing = db.scalar(
                    select(Order).where(Order.idempotency_key == key, Order.user_id == user_id)
                )
                if existing:
                    return order_data(db, existing)
            raise


def _return_quote(db, order, items=None):
    if (
        order.status not in {"confirmed", "delivered", "partially_returned"}
        or time.time() - order.created_at > 30 * 86400
    ):
        raise DomainError("This order is outside the 30-day return policy or already resolved.", 409)
    lines = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.product_id)
    ).all()
    requested = (
        items
        if items is not None
        else [
            {"product_id": line.product_id, "quantity": line.quantity - line.returned_quantity}
            for line in lines
            if line.quantity > line.returned_quantity
        ]
    )
    validated = CartInput.model_validate({"items": requested})
    quantities: dict[str, int] = {}
    for item in validated.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    if not quantities or set(quantities) - {line.product_id for line in lines}:
        raise DomainError("Select remaining items belonging to this order.", 409)
    # Allocate the exact paid amount across lines, then cumulative units. Integer
    # rounding cannot create money, even when each unit is returned separately.
    snapshot = order_data(db, order)
    gross = sum(line.unit_price * line.quantity for line in lines)
    cumulative, selected = 0, []
    for line in lines:
        start = cumulative
        cumulative += line.unit_price * line.quantity
        net = order.total * cumulative // gross - order.total * start // gross
        quantity = quantities.get(line.product_id, 0)
        if quantity > line.quantity - line.returned_quantity:
            raise DomainError("Requested quantity has already been returned or exceeds the purchase.", 409)
        if quantity:
            amount = (
                net * (line.returned_quantity + quantity) // line.quantity
                - net * line.returned_quantity // line.quantity
            )
            selected.append(
                {
                    "order_item_id": line.id,
                    "product_id": line.product_id,
                    "quantity": quantity,
                    "amount": amount,
                    "previously_returned": line.returned_quantity,
                    "unit_price": line.unit_price,
                    "product": next(
                        i["product"] for i in snapshot["items"] if i["product_id"] == line.product_id
                    ),
                }
            )
    return {
        "total": sum(i["amount"] for i in selected),
        "items": selected,
        "order": snapshot,
        "policy": "30-day item-level return",
    }


def return_quote(user_id: str, order_id: str, items=None) -> dict:
    with Session() as db:
        return _return_quote(db, owned_order(db, order_id, user_id), items)


def resolve_return(user_id: str, execution_id: str) -> dict:
    key = f"return:{execution_id}"
    with Session.begin() as db:
        execution = require_approval(db, execution_id, user_id)
        payload = execution.payload
        order = db.scalar(
            select(Order).where(Order.id == payload["order_id"], Order.user_id == user_id).with_for_update()
        )
        if order is None:
            raise DomainError("Order not found.", 404)
        existing = db.get(Return, payload["return_id"])
        if existing:
            return {
                "id": existing.id,
                "status": existing.status,
                "resolution": existing.resolution,
                "order_id": order.id,
                "amount": existing.amount,
            }
        current = _return_quote(db, order, payload.get("items"))
        if current["total"] != payload["quote"]["total"]:
            raise DomainError("Return amount changed; request a new approval.", 409)
        # Both PostgreSQL row locks and SQL compare-and-swap protect entitlements.
        for item in current["items"]:
            changed = db.execute(
                update(OrderItem)
                .where(
                    OrderItem.id == item["order_item_id"],
                    OrderItem.returned_quantity == item["previously_returned"],
                    OrderItem.returned_quantity + item["quantity"] <= OrderItem.quantity,
                )
                .values(returned_quantity=OrderItem.returned_quantity + item["quantity"])
            )
            if getattr(changed, "rowcount", 0) != 1:
                raise DomainError("Return quantities changed; request a new review.", 409)
        row = Return(
            id=payload["return_id"],
            order_id=order.id,
            user_id=user_id,
            reason=payload["reason"],
            resolution=payload["resolution"],
            status="completed",
            amount=current["total"],
        )
        db.add(row)
        db.flush()
        db.add_all(
            [
                ReturnItem(
                    return_id=row.id,
                    order_item_id=i["order_item_id"],
                    quantity=i["quantity"],
                    amount=i["amount"],
                )
                for i in current["items"]
            ]
        )
        emit(db, "refund.requested", order.id, {"return_id": row.id, "resolution": row.resolution})
        payment = db.scalar(select(Payment).where(Payment.order_id == order.id))
        if not payment or payment.status not in {"completed", "partially_refunded"}:
            raise DomainError("No eligible settled payment.", 409)
        if row.resolution == "refund":
            db.add(
                Refund(
                    order_id=order.id,
                    return_id=row.id,
                    amount=row.amount,
                    status="completed",
                    idempotency_key=key,
                )
            )
            db.flush()
            refunded = sum(db.scalars(select(Refund.amount).where(Refund.order_id == order.id)).all())
            if refunded > payment.amount:
                raise DomainError("Refund exceeds the settled payment.", 409)
            payment.status = "refunded" if refunded == payment.amount else "partially_refunded"
            emit(db, "refund.completed", order.id, {"amount": row.amount, "return_id": row.id})
        else:
            for item in current["items"]:
                mutation = db.execute(
                    update(Inventory)
                    .where(
                        Inventory.product_id == item["product_id"], Inventory.available >= item["quantity"]
                    )
                    .values(available=Inventory.available - item["quantity"], version=Inventory.version + 1)
                )
                if getattr(mutation, "rowcount", 0) != 1:
                    raise DomainError("Replacement stock is unavailable.", 409)
            db.add(
                Shipment(
                    order_id=order.id, kind="replacement", tracking_code=f"REPLACE-{row.id}", estimated_days=7
                )
            )
            emit(db, "shipment.created", order.id, {"kind": "replacement", "return_id": row.id})
        remaining = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        complete = all(i.returned_quantity == i.quantity for i in remaining)
        order.status = (
            (
                "refunded"
                if payment.status == "refunded"
                else "replacement_sent"
                if row.resolution == "replacement"
                else "returned"
            )
            if complete
            else "partially_returned"
        )
        db.add(
            AuditLog(
                user_id=user_id,
                action=f"return.{row.resolution}",
                resource_id=row.id,
                detail={"amount": row.amount, "execution_id": execution_id, "items": current["items"]},
            )
        )
        result = {
            "id": row.id,
            "status": row.status,
            "resolution": row.resolution,
            "order_id": order.id,
            "amount": row.amount,
        }
    cache.invalidate(*(f"product:{i['product_id']}" for i in current["items"]))
    return result


def cancel_order(user_id: str, execution_id: str) -> dict:
    with Session.begin() as db:
        execution = require_approval(db, execution_id, user_id)
        order = owned_order(db, execution.payload["order_id"], user_id)
        if order.status == "cancelled":
            return order_data(db, order)
        if order.status != "confirmed":
            raise DomainError("Only unshipped confirmed orders can be cancelled.", 409)
        if any(
            s.status != "processing"
            for s in db.scalars(select(Shipment).where(Shipment.order_id == order.id)).all()
        ):
            raise DomainError("Shipment has progressed; request a return instead.", 409)
        changed = db.execute(
            update(Order).where(Order.id == order.id, Order.status == "confirmed").values(status="cancelled")
        )
        if getattr(changed, "rowcount", 0) != 1:
            raise DomainError("Order state changed.", 409)
        for line in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all():
            db.execute(
                update(Inventory)
                .where(Inventory.product_id == line.product_id)
                .values(available=Inventory.available + line.quantity, version=Inventory.version + 1)
            )
        payment = db.scalar(select(Payment).where(Payment.order_id == order.id))
        assert payment is not None
        payment.status = "voided"
        for shipment in db.scalars(select(Shipment).where(Shipment.order_id == order.id)).all():
            shipment.status = "cancelled"
        emit(db, "order.cancelled", order.id, {"amount": order.total})
        db.add(AuditLog(user_id=user_id, action="order.cancelled", resource_id=order.id))
        db.flush()
        result = order_data(db, order)
    cache.invalidate(*(f"product:{i['product_id']}" for i in result["items"]))
    return result


def customer(user_id: str) -> dict:
    with Session() as db:
        user = required(db, User, user_id)
        return {"id": user.id, "name": user.name, "preferences": user.preferences}
