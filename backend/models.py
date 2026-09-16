import time
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


def uid() -> str:
    return uuid.uuid4().hex


class Entity:
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(32), primary_key=True)


class User(Entity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(ForeignKey("roles.name"), default="CUSTOMER")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)


class RefreshToken(Entity, Base):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[float] = mapped_column(Float)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Category(Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)


class Seller(Entity, Base):
    __tablename__ = "sellers"
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Product(Entity, Base):
    __tablename__ = "products"
    name: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(ForeignKey("categories.name"), index=True)
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.id"))
    price: Mapped[int] = mapped_column(Integer)
    rating: Mapped[float] = mapped_column(Float)
    warranty_months: Mapped[int] = mapped_column(Integer)
    delivery_days: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    specs: Mapped[dict] = mapped_column(JSON)
    color: Mapped[str] = mapped_column(String(16), default="#e7eaf1")
    __table_args__ = (CheckConstraint("price > 0"), CheckConstraint("rating >= 0 AND rating <= 5"))


class ProductSpecification(Entity, Base):
    __tablename__ = "product_specifications"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("product_id", "name"),)


class Inventory(Base):
    __tablename__ = "inventory"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    available: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("available >= 0"),)


class Review(Entity, Base):
    __tablename__ = "reviews"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeDocument(Entity, Base):
    __tablename__ = "knowledge_documents"
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(180))
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), unique=True)


class Cart(Entity, Base):
    __tablename__ = "carts"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)


class CartItem(Entity, Base):
    __tablename__ = "cart_items"
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("cart_id", "product_id"), CheckConstraint("quantity > 0"))


class Coupon(Base):
    __tablename__ = "coupons"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    percent: Mapped[int] = mapped_column(Integer)
    minimum: Mapped[int] = mapped_column(Integer)
    max_discount: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[float] = mapped_column(Float)
    __table_args__ = (CheckConstraint("percent >= 0 AND percent <= 100"),)


class Order(Entity, Base):
    __tablename__ = "orders"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    total: Mapped[int] = mapped_column(Integer)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(32), default="personal")
    address: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    procurement: Mapped[dict] = mapped_column(JSON, default=dict)


class OrderItem(Entity, Base):
    __tablename__ = "order_items"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[int] = mapped_column(Integer)
    returned_quantity: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("returned_quantity >= 0 AND returned_quantity <= quantity"),)


class Payment(Entity, Base):
    __tablename__ = "payments"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(32), default="safe_mock")
    reference: Mapped[str] = mapped_column(String(100), unique=True)


class Shipment(Entity, Base):
    __tablename__ = "shipments"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    tracking_code: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    estimated_days: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32), default="original")


class Return(Entity, Base):
    __tablename__ = "returns"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))

    amount: Mapped[int] = mapped_column(Integer, default=0)


class Refund(Entity, Base):
    __tablename__ = "refunds"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.id"), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)


class AgentExecution(Entity, Base):
    __tablename__ = "agent_executions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_key: Mapped[str | None] = mapped_column(String(180), unique=True, nullable=True)


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.id"), index=True)
    stage: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Approval(Entity, Base):
    __tablename__ = "approvals"
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.id"), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    risk_score: Mapped[int] = mapped_column(Integer)
    required_role: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="")
    request_hash: Mapped[str] = mapped_column(String(64))


class AuditLog(Entity, Base):
    __tablename__ = "audit_logs"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class OutboxEvent(Entity, Base):
    __tablename__ = "outbox_events"
    type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConsumerReceipt(Base):
    __tablename__ = "consumer_receipts"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    consumer: Mapped[str] = mapped_column(String(64), primary_key=True)


class SupportTicket(Entity, Base):
    __tablename__ = "support_tickets"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(180), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[float] = mapped_column(Float)


class ReturnItem(Entity, Base):
    __tablename__ = "return_items"
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.id"), index=True)
    order_item_id: Mapped[str] = mapped_column(ForeignKey("order_items.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("return_id", "order_item_id"),
        CheckConstraint("quantity > 0 AND amount >= 0"),
    )


class Notification(Entity, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    message: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class DomainProjection(Base):
    __tablename__ = "domain_projections"
    aggregate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    consumer: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


class DeadLetter(Entity, Base):
    __tablename__ = "dead_letters"
    source_key: Mapped[str] = mapped_column(String(180), unique=True)
    envelope: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")


class AgentRun(Entity, Base):
    __tablename__ = "agent_runs"
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.id"), index=True)
    agent: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32))
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
