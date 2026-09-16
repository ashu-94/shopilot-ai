import asyncio
import hashlib
import json
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select, text, update
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend import auth, catalog, commerce, documents, events, operations, workflows
from backend.cache import cache
from backend.config import settings
from backend.db import Session, engine
from backend.errors import DomainError
from backend.models import (
    AgentExecution,
    AgentRun,
    Approval,
    AuditLog,
    DeadLetter,
    Notification,
    OutboxEvent,
    RefreshToken,
    User,
    WorkflowEvent,
)
from backend.observability import HTTP_LATENCY, HTTP_REQUESTS, configure
from backend.repositories import required
from backend.routing import classify
from backend.schemas import (
    CartInput,
    CheckoutInput,
    DecisionInput,
    LoginInput,
    MissionInput,
    ReplayInput,
    ReturnInput,
)
from backend.security import RequestBoundary
from backend.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings().validate_runtime()
    if settings().seed_demo:
        seed()
    runner = workflows.WorkflowRunner()
    await runner.open()
    app.state.runner = runner
    tasks = [
        asyncio.create_task(runner.poll()),
        asyncio.create_task(events.relay_loop()),
        asyncio.create_task(events.consume_loop()),
    ]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await runner.close()


app = FastAPI(
    title="ShopPilot AI",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None if settings().app_env == "production" else "/docs",
    redoc_url=None,
)
app.add_middleware(RequestBoundary)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings().allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID"],
)
configure(app, engine)


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})


@app.middleware("http")
async def observe(request: Request, call_next):
    started = time.perf_counter()
    try:
        if request.url.path.startswith("/api") and request.method != "OPTIONS":
            await asyncio.to_thread(
                cache.rate_limit, request.client.host if request.client else "unknown", 300
            )
        response = await call_next(request)
    except DomainError as exc:
        response = JSONResponse(
            status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}}
        )
    route = request.scope.get("route")
    label = route.path if route else "unmatched"
    HTTP_REQUESTS.labels(request.method, label, response.status_code).inc()
    HTTP_LATENCY.labels(label).observe(time.perf_counter() - started)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if settings().app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "not_ready", "dependency": "database"}, status_code=503)
    return {"status": "ready", "database": engine.dialect.name, "payments": "safe_mock"}


@app.get("/metrics", include_in_schema=False)
def prometheus():
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


@app.post("/api/auth/login")
def login(body: LoginInput, request: Request, response: Response):
    cache.rate_limit(f"login:{request.client.host if request.client else 'unknown'}", 15)
    return auth.login(body.email, body.password, response)


@app.post("/api/auth/refresh")
def refresh(request: Request, response: Response):
    return auth.refresh(request, response)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    raw = request.cookies.get("shopilot_refresh", "")
    with Session.begin() as db:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.digest == hashlib.sha256(raw.encode()).hexdigest())
            .values(revoked=True)
        )
    response.delete_cookie("shopilot_refresh", path="/api/auth")
    return {"status": "signed_out"}


@app.get("/api/auth/me")
def me(user: User = Depends(auth.current_user)):
    return auth.public_user(user)


@app.get("/api/config")
def config():
    return {
        "demo": settings().app_env == "development",
        "llm_provider": settings().llm_provider,
        "payment_provider": "safe_mock",
        "currency": "INR",
    }


@app.get("/api/products")
def products(q: str = "", category: str = "", max_price: int = 10000000):
    return catalog.search_products(q[:150], category[:40], min(max_price, 100000000))


@app.get("/api/products/{product_id}")
def product(product_id: str):
    return {**catalog.get_product(product_id), "reviews": catalog.reviews(product_id)}


@app.get("/api/cart")
def get_cart(user: User = Depends(auth.current_user)):
    return commerce.cart(user.id)


@app.put("/api/cart")
def set_cart(body: CartInput, user: User = Depends(auth.current_user)):
    return commerce.set_cart(user.id, [item.model_dump() for item in body.items])


@app.post("/api/missions", status_code=202)
def mission(
    body: MissionInput,
    user: User = Depends(auth.current_user),
    idempotency_key: str | None = Header(default=None),
):
    intent = classify(body.query, body.mode)
    if intent == "procurement" and user.role not in {"BUSINESS_USER", "MANAGER", "ADMIN"}:
        raise DomainError("Use a business account for procurement.", 403)
    workflows.input_guard(body.query)
    if intent == "procurement" and body.procurement is None:
        raise DomainError("Procurement requires organization, billing and delivery details.", 422)
    return workflows.create_execution(
        user.id,
        intent,
        body.query,
        {"budget": body.budget, "procurement": body.procurement.model_dump() if body.procurement else {}},
        idempotency_key,
    )


@app.post("/api/checkout", status_code=202)
def checkout(body: CheckoutInput, user: User = Depends(auth.current_user), idempotency_key: str = Header()):
    replay = workflows.replay_execution(user.id, "checkout", idempotency_key, body.model_dump())
    if replay:
        return replay
    current = commerce.cart(user.id)
    if not current["items"]:
        raise DomainError("Add products to your cart before checkout.")
    payload = {
        "items": [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in current["items"]],
        "quote": current,
        "client_request": body.model_dump(),
        **body.model_dump(),
    }
    return workflows.create_execution(
        user.id, "checkout", "Confirm and purchase the selected cart", payload, idempotency_key
    )


@app.get("/api/orders")
def orders(user: User = Depends(auth.current_user)):
    return commerce.history(user.id)


@app.get("/api/orders/{order_id}")
def order(order_id: str, user: User = Depends(auth.current_user)):
    return commerce.get_order(user.id, order_id)


@app.get("/api/orders/{order_id}/purchase-order")
def purchase_order(order_id: str, user: User = Depends(auth.current_user)):
    return JSONResponse(
        documents.purchase_order(user.id, order_id),
        headers={"Content-Disposition": f'attachment; filename="PO-{order_id[:12]}.json"'},
    )


@app.post("/api/orders/{order_id}/cancel", status_code=202)
def cancel(order_id: str, user: User = Depends(auth.current_user), idempotency_key: str = Header()):
    current = commerce.get_order(user.id, order_id)
    return workflows.create_execution(
        user.id,
        "cancel",
        "Cancel my confirmed order",
        {"order_id": order_id, "quote": {"total": current["total"]}},
        idempotency_key,
    )


@app.post("/api/returns", status_code=202)
def returns(body: ReturnInput, user: User = Depends(auth.current_user), idempotency_key: str = Header()):
    replay = workflows.replay_execution(user.id, "return", idempotency_key, body.model_dump())
    if replay:
        return replay
    current = commerce.return_quote(
        user.id, body.order_id, [i.model_dump() for i in body.items] if body.items else None
    )
    # Stable return id makes execution replay safe. Key scope includes authenticated user.
    return_id = hashlib.sha256(f"{user.id}:{idempotency_key}".encode()).hexdigest()[:32]
    return workflows.create_execution(
        user.id,
        "return",
        body.reason,
        {**body.model_dump(), "quote": current, "return_id": return_id, "client_request": body.model_dump()},
        idempotency_key,
    )


@app.get("/api/executions")
def executions(user: User = Depends(auth.current_user)):
    with Session() as db:
        return [
            workflows.execution_data(row)
            for row in db.scalars(
                select(AgentExecution)
                .where(AgentExecution.user_id == user.id)
                .order_by(AgentExecution.created_at.desc())
                .limit(30)
            ).all()
        ]


def owned_execution(db, execution_id: str, user: User):
    row = required(db, AgentExecution, execution_id)
    if not row or row.user_id != user.id:
        raise DomainError("Workflow not found.", 404)
    return row


@app.get("/api/executions/{execution_id}")
def execution(execution_id: str, user: User = Depends(auth.current_user)):
    with Session() as db:
        return workflows.execution_data(owned_execution(db, execution_id, user))


@app.post("/api/executions/{execution_id}/retry")
def retry(execution_id: str, user: User = Depends(auth.current_user)):
    with Session.begin() as db:
        row = owned_execution(db, execution_id, user)
        if row.status != "failed":
            raise DomainError("Only failed workflows can be retried.", 409)
        row.status, row.lease_until, row.error = "queued", 0, None
        return workflows.execution_data(row)


@app.get("/api/executions/{execution_id}/events")
async def stream(
    execution_id: str, request: Request, after: int = 0, user: User = Depends(auth.current_user)
):
    with Session() as db:
        owned_execution(db, execution_id, user)
    try:
        initial_cursor = max(after, int(request.headers.get("Last-Event-ID", "0") or 0))
    except ValueError:
        raise DomainError("Last-Event-ID must be an integer.", 400) from None

    async def generate():
        cursor = initial_cursor
        while not await request.is_disconnected():
            with Session() as db:
                rows = db.scalars(
                    select(WorkflowEvent)
                    .where(WorkflowEvent.execution_id == execution_id, WorkflowEvent.id > cursor)
                    .order_by(WorkflowEvent.id)
                ).all()
                current = required(db, AgentExecution, execution_id)
                status = current.status
            for row in rows:
                cursor = row.id
                yield f"id: {row.id}\ndata: {json.dumps({'id': row.id, 'stage': row.stage, 'message': row.message})}\n\n"
            if status in {"completed", "failed", "rejected", "awaiting_approval"}:
                yield f"event: done\ndata: {json.dumps({'status': status})}\n\n"
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/approvals")
def approvals(user: User = Depends(auth.current_user)):
    with Session() as db:
        statement = select(Approval)
        if user.role not in {"MANAGER", "ADMIN"}:
            statement = statement.where(Approval.user_id == user.id)
        rows = db.scalars(statement.order_by(Approval.created_at.desc()).limit(60)).all()
        return [
            {
                "id": a.id,
                "execution_id": a.execution_id,
                "amount": a.amount,
                "reason": a.reason,
                "risk_score": a.risk_score,
                "required_role": a.required_role,
                "status": a.status,
                "feedback": a.feedback,
                "customer": required(db, User, a.user_id).name,
                "kind": required(db, AgentExecution, a.execution_id).kind,
                "quote": required(db, AgentExecution, a.execution_id).payload.get("quote"),
                "procurement": required(db, AgentExecution, a.execution_id).payload.get("procurement", {}),
                "can_decide": (a.required_role == "OWNER" and a.user_id == user.id)
                or (
                    a.required_role == "MANAGER"
                    and user.role in {"MANAGER", "ADMIN"}
                    and a.user_id != user.id
                ),
            }
            for a in rows
        ]


@app.post("/api/approvals/{approval_id}/decision")
def decision(approval_id: str, body: DecisionInput, user: User = Depends(auth.current_user)):
    return workflows.decide(user, approval_id, body.decision, body.feedback)


@app.get("/api/operations")
def ops(user: User = Depends(auth.require_roles("ADMIN", "MANAGER"))):
    return operations.metrics()


@app.get("/api/admin")
def admin(user: User = Depends(auth.require_roles("ADMIN"))):
    return operations.admin_summary()


@app.get("/api/notifications")
def notifications(user: User = Depends(auth.current_user)):
    with Session() as db:
        return [
            {
                "id": n.id,
                "message": n.message,
                "order_id": n.order_id,
                "read": n.read,
                "created_at": n.created_at,
            }
            for n in db.scalars(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc())
                .limit(100)
            ).all()
        ]


@app.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id: str, user: User = Depends(auth.current_user)):
    with Session.begin() as db:
        row = db.get(Notification, notification_id)
        if not row or row.user_id != user.id:
            raise DomainError("Notification not found.", 404)
        row.read = True
    return {"status": "read"}


@app.get("/api/executions/{execution_id}/agents")
def agent_runs(execution_id: str, user: User = Depends(auth.current_user)):
    with Session() as db:
        owned_execution(db, execution_id, user)
        return [
            {"agent": r.agent, "status": r.status, "duration_ms": r.duration_ms, "detail": r.detail}
            for r in db.scalars(
                select(AgentRun).where(AgentRun.execution_id == execution_id).order_by(AgentRun.created_at)
            ).all()
        ]


@app.get("/api/admin/recovery")
def recovery(user: User = Depends(auth.require_roles("ADMIN"))):
    with Session() as db:
        return {
            "outbox": [
                {"id": e.id, "type": e.type, "attempts": e.attempts, "error": e.error}
                for e in db.scalars(
                    select(OutboxEvent).where(OutboxEvent.published.is_(False)).limit(100)
                ).all()
            ],
            "dead_letters": [
                {"id": e.id, "reason": e.reason, "source": e.source_key, "status": e.status}
                for e in db.scalars(select(DeadLetter).where(DeadLetter.status == "pending").limit(100)).all()
            ],
            "workflows": [
                workflows.execution_data(e)
                for e in db.scalars(
                    select(AgentExecution)
                    .where(
                        AgentExecution.status.in_(["failed", "running"]),
                        AgentExecution.lease_until < time.time(),
                    )
                    .limit(100)
                ).all()
            ],
        }


@app.post("/api/admin/outbox/{event_id}/replay")
def replay_outbox(event_id: str, body: ReplayInput, user: User = Depends(auth.require_roles("ADMIN"))):
    with Session.begin() as db:
        event = required(db, OutboxEvent, event_id)
        if event.published:
            raise DomainError("Published events cannot be reset through recovery.", 409)
        event.attempts, event.next_attempt_at, event.error = 0, 0, None
        db.add(
            AuditLog(
                user_id=user.id,
                action="recovery.outbox",
                resource_id=event_id,
                detail={"reason": body.reason},
            )
        )
    return {"status": "queued"}


@app.post("/api/admin/workflows/{execution_id}/recover")
def recover_workflow(execution_id: str, body: ReplayInput, user: User = Depends(auth.require_roles("ADMIN"))):
    with Session.begin() as db:
        changed = db.execute(
            update(AgentExecution)
            .where(
                AgentExecution.id == execution_id,
                AgentExecution.status.in_(["failed", "running"]),
                AgentExecution.lease_until < time.time(),
            )
            .values(status="queued", error=None, lease_until=0)
        )
        if getattr(changed, "rowcount", 0) != 1:
            raise DomainError("Only failed or expired running workflows can be recovered.", 409)
        db.add(
            AuditLog(
                user_id=user.id,
                action="recovery.workflow",
                resource_id=execution_id,
                detail={"reason": body.reason},
            )
        )
    return {"status": "queued"}


@app.post("/api/admin/dead-letters/{letter_id}/replay")
def replay_dead_letter(letter_id: str, body: ReplayInput, user: User = Depends(auth.require_roles("ADMIN"))):
    with Session.begin() as db:
        letter = required(db, DeadLetter, letter_id)
        if letter.status != "pending":
            raise DomainError("Dead letter already handled.", 409)
        try:
            envelope = json.loads(letter.envelope["raw"])
            events.validate_envelope(envelope)
        except (ValueError, KeyError, TypeError):
            raise DomainError(
                "Event schema is still invalid. Correct the producer and republish a valid event.", 409
            ) from None
        if not db.get(OutboxEvent, envelope["id"]):
            db.add(
                OutboxEvent(
                    id=envelope["id"],
                    type=envelope["type"],
                    aggregate_id=envelope["aggregate_id"],
                    payload=envelope["payload"],
                )
            )
        letter.status = "replayed"
        db.add(
            AuditLog(
                user_id=user.id,
                action="recovery.dead_letter",
                resource_id=letter_id,
                detail={"reason": body.reason},
            )
        )
    return {"status": "queued"}
