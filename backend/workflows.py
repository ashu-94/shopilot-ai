import asyncio
import logging
import os
import time
import uuid
from contextlib import AsyncExitStack
from typing import Any, TypedDict

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from backend import commerce, documents, llm, rag, recommendations, review_analysis, tools
from backend.config import settings
from backend.db import Session
from backend.errors import DomainError
from backend.models import AgentExecution, Approval, AuditLog, Refund, SupportTicket, User, WorkflowEvent, uid
from backend.observability import WORKFLOWS
from backend.policies import approval_policy, fingerprint, input_guard, risk
from backend.repositories import required
from backend.specialists import Specialist

log = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    user_id: str
    thread_id: str
    user_query: str
    kind: str
    intent: str
    extracted_constraints: dict
    selected_agents: list[str]
    products: list[dict]
    retrieved_context: dict
    recommendations: dict
    risk_score: int
    approval_required: bool
    approval_reason: str
    human_feedback: dict
    errors: list[str]
    retry_count: int
    result: dict
    preferences: dict
    assessment: dict
    analytics: dict


def public_event(execution_id: str, stage: str, message: str):
    with Session.begin() as db:
        db.add(WorkflowEvent(execution_id=execution_id, stage=stage, message=message))


def execution_data(row: AgentExecution) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "query": row.query,
        "status": row.status,
        "result": row.result,
        "error": row.error,
        "created_at": row.created_at,
        "duration_ms": row.duration_ms,
        "tokens": row.tokens,
        "trace_id": row.trace_id,
    }


def create_execution(user_id: str, kind: str, query: str, payload: dict, key: str | None = None) -> dict:
    request_key = f"{user_id}:{kind}:{key}" if key else None
    if key and (len(key) > 100 or len(key) < 8):
        raise DomainError("Idempotency-Key must have 8–100 characters.")
    try:
        with Session.begin() as db:
            if request_key:
                existing = db.scalar(select(AgentExecution).where(AgentExecution.request_key == request_key))
                if existing:
                    if existing.query != query or existing.payload.get("request_fingerprint") != fingerprint(
                        payload
                    ):
                        raise DomainError("Idempotency key was used for a different request.", 409)
                    return execution_data(existing)
            row = AgentExecution(
                user_id=user_id,
                kind=kind,
                query=query,
                payload={**payload, "request_fingerprint": fingerprint(payload)},
                request_key=request_key,
            )
            db.add(row)
            db.flush()
            return execution_data(row)
    except IntegrityError:
        with Session() as db:
            existing = db.scalar(select(AgentExecution).where(AgentExecution.request_key == request_key))
            if existing and existing.payload.get("request_fingerprint") == fingerprint(payload):
                return execution_data(existing)
        raise DomainError("Conflicting workflow request.", 409) from None


def replay_execution(user_id: str, kind: str, key: str, client_request: dict) -> dict | None:
    with Session() as db:
        existing = db.scalar(
            select(AgentExecution).where(AgentExecution.request_key == f"{user_id}:{kind}:{key}")
        )
        if existing:
            if existing.payload.get("client_request") != client_request:
                raise DomainError("Idempotency key was used for a different request.", 409)
            return execution_data(existing)
    return None


async def supervisor(state: AgentState):
    public_event(state["thread_id"], "understanding", "Understanding your goal")
    input_guard(state["user_query"])
    kind = state["kind"]
    agents = ["shopping", "search", "recommendation", "compatibility", "inventory", "budget"]
    if kind == "procurement":
        agents += ["procurement", "risk", "order"]
    elif kind in {"checkout", "return", "cancel"}:
        agents = ["risk", "refund" if kind == "return" else "order"]
    elif kind == "support":
        agents = ["support"]
    return {"intent": kind, "selected_agents": agents + ["analytics"], "retry_count": 0, "errors": []}


async def planning(state: AgentState):
    public_event(state["thread_id"], "planning", "Planning your purchasing requirements")
    with Session() as db:
        payload = required(db, AgentExecution, state["thread_id"]).payload
    constraints = await llm.understand(state["user_query"], state["kind"], payload.get("budget"))
    preferences = await tools.call("shopping", state["user_id"], "get_preferences")
    return {"extracted_constraints": constraints, "preferences": preferences["preferences"]}


async def search(state: AgentState):
    public_event(state["thread_id"], "searching", "Searching the catalog through Product MCP")
    groups = await asyncio.gather(
        *(
            tools.call(
                "search",
                state["user_id"],
                "search_products",
                category=category,
                max_price=state["extracted_constraints"]["budget"],
            )
            for category in state["extracted_constraints"]["categories"]
        )
    )
    return {"products": [product for group in groups for product in group]}


async def retrieval(state: AgentState):
    public_event(state["thread_id"], "retrieving", "Retrieving specifications, reviews and policy evidence")
    context = await rag.retrieve(state["user_query"], [p["id"] for p in state["products"]])
    if not context["grounded"]:
        raise DomainError("No reliable evidence was found for these products.", 409)
    return {"retrieved_context": context}


async def inventory_agent(state: AgentState):
    public_event(state["thread_id"], "inventory", "Inventory agent is verifying quantities")
    stocks = await asyncio.gather(
        *(
            tools.call("inventory", state["user_id"], "check_inventory", product_id=p["id"])
            for p in state["products"]
        )
    )
    return {
        "products": [
            {**p, "stock": stock["available"]} for p, stock in zip(state["products"], stocks, strict=True)
        ]
    }


async def recommendation_agent(state: AgentState):
    public_event(
        state["thread_id"],
        "recommendation",
        "Recommendation agent is ranking complete bundles and analyzing reviews",
    )
    result = recommendations.optimize(state["products"], state["extracted_constraints"], state["preferences"])
    reviews = await asyncio.gather(
        *(
            tools.call("recommendation", state["user_id"], "get_product_reviews", product_id=p["id"])
            for p in result["products"]
        )
    )
    evidence = state["retrieved_context"]["evidence"]
    result["products"] = [
        {
            **p,
            "evidence": [e for e in evidence if e["product_id"] == p["id"]],
            "reason": f"Meets the catalog constraints for {p['category']} within the complete bundle budget.",
            "reviews": review,
            "review_analysis": review_analysis.analyze(review),
        }
        for p, review in zip(result["products"], reviews, strict=True)
    ]
    return {"recommendations": result}


async def compatibility_agent(state: AgentState):
    specs = await tools.call(
        "compatibility",
        state["user_id"],
        "compare_products",
        product_ids=[p["id"] for p in state["recommendations"]["products"]],
    )
    return {
        "recommendations": {
            **state["recommendations"],
            "warnings": recommendations.compatibility(specs, state["extracted_constraints"]),
        }
    }


async def budget_agent(state: AgentState):
    result, constraints = dict(state["recommendations"]), state["extracted_constraints"]
    coupon = await tools.call("budget", state["user_id"], "find_best_coupon", subtotal=result["subtotal"])
    result.update(
        {
            "total": result["subtotal"] - coupon["discount"],
            "discount": coupon["discount"],
            "coupon": coupon["code"],
            "budget": constraints["budget"],
            "remaining": constraints["budget"] - result["subtotal"] + coupon["discount"],
            "constraints": constraints,
            "retrieval": {k: v for k, v in state["retrieved_context"].items() if k != "evidence"},
        }
    )
    if result["remaining"] < 0:
        raise DomainError("The bundle exceeds the approved budget.", 409)
    explanation = await llm.explain(state["user_query"], {"mode": state["kind"]})
    result.update({"explanation": explanation["text"], "provider": explanation["provider"]})
    with Session.begin() as db:
        row = required(db, AgentExecution, state["thread_id"])
        row.tokens = explanation["tokens"] + constraints.get("planning_tokens", 0)
        row.cost = explanation["cost"] + constraints.get("planning_cost", 0)
    return {"recommendations": result, "result": result}


async def procurement_agent(state: AgentState):
    from datetime import date

    from backend.schemas import ProcurementDetails

    with Session.begin() as db:
        row = required(db, AgentExecution, state["thread_id"])
        details = ProcurementDetails.model_validate(row.payload.get("procurement", {})).model_dump()
        deadline = date.fromisoformat(details["requested_delivery_date"])
        days = (deadline - date.today()).days
        if days < max(p["delivery_days"] for p in state["recommendations"]["products"]):
            raise DomainError(
                "Requested procurement delivery date is earlier than catalog delivery estimates.", 409
            )
        items = [
            {"product_id": p["id"], "quantity": state["recommendations"]["quantity"]}
            for p in state["recommendations"]["products"]
        ]
        row.payload = {
            **row.payload,
            "items": items,
            "quote": commerce.quote(db, items),
            "address": details["delivery_address"],
            "procurement": details,
        }
    return {"result": {**state["result"], "procurement": details}}


async def risk_agent(state: AgentState):
    with Session() as db:
        row = required(db, AgentExecution, state["thread_id"])
        user = required(db, User, state["user_id"])
        refunds = (
            db.scalar(
                select(func.count())
                .select_from(Refund)
                .join(commerce.Order, Refund.order_id == commerce.Order.id)
                .where(commerce.Order.user_id == user.id)
            )
            or 0
        )
        failures = (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.user_id == user.id,
                    AuditLog.action == "payment.failed",
                    AuditLog.created_at > time.time() - 86400,
                )
            )
            or 0
        )
        orders = db.scalars(select(commerce.Order).where(commerce.Order.user_id == user.id)).all()
        address = row.payload.get("address")
        changed_address = bool(address and orders and address not in {o.address for o in orders})
        assessment = risk(
            row.payload["quote"]["total"],
            user.created_at,
            refunds=refunds,
            failed_payments=failures,
            shipping_anomaly=changed_address,
        )
    return {"assessment": assessment, "risk_score": assessment["score"]}


async def analytics_agent(state: AgentState):
    summary = {
        "intent": state["kind"],
        "selected_products": len(state.get("recommendations", {}).get("products", [])),
        "total": state.get("result", {}).get("total"),
        "outcome": state.get("human_feedback", {}).get("decision", "completed"),
    }
    with Session.begin() as db:
        db.add(
            AuditLog(
                user_id=state["user_id"],
                action="agent.analytics",
                resource_id=state["thread_id"],
                detail=summary,
            )
        )
    return {"analytics": summary}


async def review(state: AgentState):
    execution_id = state["thread_id"]
    with Session.begin() as db:
        row = required(db, AgentExecution, execution_id)
        amount = row.payload["quote"]["total"]
        user = required(db, User, state["user_id"])
        assessment = state.get("assessment") or risk(amount, user.created_at)
        policy = approval_policy(state["kind"], amount, assessment["score"])
        approval = db.scalar(select(Approval).where(Approval.execution_id == execution_id))
        if not approval:
            db.add(
                Approval(
                    execution_id=execution_id,
                    user_id=user.id,
                    amount=amount,
                    reason=policy["reason"],
                    risk_score=assessment["score"],
                    required_role=policy["role"],
                    request_hash=fingerprint(row.payload),
                )
            )
            db.add(WorkflowEvent(execution_id=execution_id, stage="approval", message=policy["reason"]))
    # No side effects follow until LangGraph has persisted this interrupt and received a decision.
    decision = interrupt(
        {
            "execution_id": execution_id,
            "amount": amount,
            "reason": policy["reason"],
            "risk_score": assessment["score"],
            "required_role": policy["role"],
        }
    )
    return {
        "human_feedback": decision,
        "approval_required": True,
        "approval_reason": policy["reason"],
        "risk_score": assessment["score"],
    }


async def transaction(state: AgentState):
    if state.get("human_feedback", {}).get("decision") != "approve":
        return {"result": {**state.get("result", {}), "decision": "rejected"}}
    public_event(
        state["thread_id"], "checkout", "Executing the approved transaction with the safe mock provider"
    )
    if state["kind"] == "return":
        result = await tools.call(
            "refund", state["user_id"], "refund_payment", execution_id=state["thread_id"]
        )
        return {"result": {"return": result}}
    if state["kind"] == "cancel":
        result = await tools.call("order", state["user_id"], "cancel_order", execution_id=state["thread_id"])
    else:
        result = await tools.call("order", state["user_id"], "create_order", execution_id=state["thread_id"])
        await tools.call("order", state["user_id"], "verify_payment", order_id=result["id"])
        await tools.call("order", state["user_id"], "track_shipment", order_id=result["id"])
        if state["kind"] == "procurement":
            try:
                result["purchase_order"] = await asyncio.to_thread(
                    documents.archive_purchase_order, state["user_id"], result["id"]
                )
            except Exception:
                result["purchase_order"] = {
                    "status": "archive_unavailable",
                    "document_number": f"PO-{result['id'][:12].upper()}",
                }
                public_event(
                    state["thread_id"],
                    "storage",
                    "Purchase order available on demand; object archive is temporarily unavailable",
                )
    return {"result": {**state.get("result", {}), "order": result}}


async def support(state: AgentState):
    public_event(state["thread_id"], "support", "Retrieving your purchases and relevant support evidence")
    orders = await tools.call("support", state["user_id"], "get_customer_orders")
    query = state["user_query"].lower()
    categories = [
        category
        for category, words in recommendations.CATEGORIES.items()
        if any(word in query for word in words)
    ]
    matched = [
        o
        for o in orders
        if any(
            p["product"]["category"] in categories or p["product"]["name"].lower() in query
            for p in o["items"]
        )
    ]
    order = (matched or ([] if categories else orders) or [None])[0]
    if not order:
        return {
            "result": {
                "answer": "I couldn't find an owned product. Place a demo order first, then describe the issue.",
                "evidence": [],
            }
        }
    context = await rag.retrieve(state["user_query"], [p["product_id"] for p in order["items"]], support=True)
    with Session.begin() as db:
        ticket = db.get(SupportTicket, state["thread_id"])
        if not ticket:
            ticket = SupportTicket(
                id=state["thread_id"],
                user_id=state["user_id"],
                order_id=order["id"],
                query=state["user_query"],
                evidence=context["evidence"],
            )
            db.add(ticket)
    return {
        "result": {
            "ticket_id": state["thread_id"],
            "order_id": order["id"],
            "answer": "I've opened a support request for your purchase. Is the issue present all the time, and was there visible damage on arrival? For electrical products, disconnect power before checking external cables; do not open the housing. This guidance cannot establish a physical diagnosis. For damage, use Returns to request a reviewed refund or replacement.",
            "evidence": context["evidence"],
            "policy": "Eligibility is rechecked when you submit a return.",
        }
    }


def build_graph(checkpointer):
    graph = StateGraph(AgentState)
    specialists = [
        Specialist(
            "shopping", "Interpret the goal and customer preferences", planning, "extracted_constraints"
        ),
        Specialist("search", "Find catalog candidates meeting explicit constraints", search, "products"),
        Specialist(
            "inventory", "Check available quantities through Inventory MCP", inventory_agent, "products"
        ),
        Specialist(
            "recommendation",
            "Rank complete bundles with review evidence",
            recommendation_agent,
            "recommendations",
        ),
        Specialist(
            "compatibility",
            "Validate interfaces and disclose unknown compatibility",
            compatibility_agent,
            "recommendations",
        ),
        Specialist(
            "budget", "Enforce the complete budget and select a valid coupon", budget_agent, "recommendations"
        ),
        Specialist(
            "procurement",
            "Validate business terms, delivery date and approval payload",
            procurement_agent,
            "result",
        ),
        Specialist(
            "risk", "Assess durable account, refund, payment and address signals", risk_agent, "assessment"
        ),
        Specialist("order", "Execute only the approved idempotent order transaction", transaction, "result"),
        Specialist("refund", "Resolve approved item return entitlements", transaction, "result"),
        Specialist("support", "Find owned purchases and grounded support evidence", support, "result"),
        Specialist("analytics", "Publish a minimal workflow outcome summary", analytics_agent, "analytics"),
    ]
    for agent in specialists:
        graph.add_node(agent.name, agent.compile(AgentState))
    graph.add_node("supervisor", supervisor)
    graph.add_node("retrieval", retrieval)
    graph.add_node("review", review)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda s: (
            "risk"
            if s["kind"] in {"checkout", "return", "cancel"}
            else "support"
            if s["kind"] == "support"
            else "shopping"
        ),
    )
    for left, right in [
        ("shopping", "search"),
        ("search", "retrieval"),
        ("retrieval", "inventory"),
        ("inventory", "recommendation"),
        ("recommendation", "compatibility"),
        ("compatibility", "budget"),
        ("procurement", "risk"),
        ("risk", "review"),
        ("order", "analytics"),
        ("refund", "analytics"),
        ("support", "analytics"),
    ]:
        graph.add_edge(left, right)
    graph.add_conditional_edges(
        "budget", lambda s: "procurement" if s["kind"] == "procurement" else "analytics"
    )
    graph.add_conditional_edges("review", lambda s: "refund" if s["kind"] == "return" else "order")
    graph.add_edge("analytics", END)
    return graph.compile(checkpointer=checkpointer)


class WorkflowRunner:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.graph: Any = None
        self.owner = uid()
        self.running: set[asyncio.Task] = set()

    async def open(self):
        saver: Any
        url = settings().checkpoint_url
        if url.startswith("postgresql"):
            saver = await self.stack.enter_async_context(AsyncPostgresSaver.from_conn_string(url))
        else:
            saver = await self.stack.enter_async_context(AsyncSqliteSaver.from_conn_string(url))
        await saver.setup()
        self.graph = build_graph(saver)

    async def close(self):
        for task in self.running:
            task.cancel()
        await asyncio.gather(*self.running, return_exceptions=True)
        await self.stack.aclose()

    async def renew(self, execution_id):
        while True:
            await asyncio.sleep(15)
            with Session.begin() as db:
                db.execute(
                    update(AgentExecution)
                    .where(AgentExecution.id == execution_id, AgentExecution.lease_owner == self.owner)
                    .values(lease_until=time.time() + 90)
                )

    async def execute(self, execution_id: str):
        started = time.perf_counter()
        heartbeat = asyncio.create_task(self.renew(execution_id))
        try:
            with Session() as db:
                row = required(db, AgentExecution, execution_id)
                initial = {
                    "user_id": row.user_id,
                    "thread_id": row.id,
                    "user_query": row.query,
                    "kind": row.kind,
                }
                approval = db.scalar(select(Approval).where(Approval.execution_id == row.id))
                decision = (
                    {
                        "decision": "approve" if approval.status == "approved" else "reject",
                        "feedback": approval.feedback,
                    }
                    if approval and approval.status in {"approved", "rejected"}
                    else None
                )
            config = {
                "configurable": {"thread_id": execution_id},
                "recursion_limit": 25,
                "run_id": uuid.UUID(execution_id),
                "run_name": f"shopilot-{row.kind}",
                "metadata": {"execution_id": execution_id},
            }
            snapshot = await self.graph.aget_state(config)
            graph_input: Any = (
                Command(resume=decision)
                if decision and snapshot.interrupts
                else None
                if snapshot.values
                else initial
            )
            result = await self.graph.ainvoke(graph_input, config=config)
            snapshot = await self.graph.aget_state(config)
            status = (
                "awaiting_approval"
                if snapshot.interrupts
                else "rejected"
                if result.get("human_feedback", {}).get("decision") == "reject"
                else "completed"
            )
            with Session.begin() as db:
                row = required(db, AgentExecution, execution_id)
                row.status, row.result, row.error = status, result.get("result", {}), None
                row.duration_ms += (time.perf_counter() - started) * 1000
                row.lease_until = 0
                if os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and os.environ.get(
                    "LANGSMITH_API_KEY"
                ):
                    row.trace_id = execution_id
            public_event(
                execution_id,
                status,
                "Waiting for human review"
                if status == "awaiting_approval"
                else "Workflow completed"
                if status == "completed"
                else "Request rejected; no transaction executed",
            )
            WORKFLOWS.labels(row.kind, status).observe(time.perf_counter() - started)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Workflow failed: %s", execution_id)
            message = (
                exc.message
                if isinstance(exc, DomainError)
                else "A workflow dependency failed. Retry this workflow or review the server logs."
            )
            with Session.begin() as db:
                row = required(db, AgentExecution, execution_id)
                row.status, row.error, row.lease_until = "failed", message, 0
                row.duration_ms += (time.perf_counter() - started) * 1000
                if isinstance(exc, DomainError) and exc.code == "payment_failed":
                    db.add(
                        AuditLog(
                            user_id=row.user_id,
                            action="payment.failed",
                            resource_id=execution_id,
                            detail={"provider": "safe_mock"},
                        )
                    )
            public_event(execution_id, "failed", message)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)

    async def poll(self):
        while True:
            self.running = {task for task in self.running if not task.done()}
            if len(self.running) < 4:
                with Session.begin() as db:
                    ids = db.scalars(
                        select(AgentExecution.id)
                        .where(
                            AgentExecution.status.in_(["queued", "running"]),
                            AgentExecution.lease_until < time.time(),
                        )
                        .order_by(AgentExecution.created_at)
                        .limit(4 - len(self.running))
                    ).all()
                    claimed = []
                    for execution_id in ids:
                        result = db.execute(
                            update(AgentExecution)
                            .where(
                                AgentExecution.id == execution_id,
                                AgentExecution.lease_until < time.time(),
                                AgentExecution.status.in_(["queued", "running"]),
                            )
                            .values(status="running", lease_until=time.time() + 90, lease_owner=self.owner)
                        )
                        if getattr(result, "rowcount", 0) == 1:
                            claimed.append(execution_id)
                for execution_id in claimed:
                    self.running.add(asyncio.create_task(self.execute(execution_id)))
            await asyncio.sleep(0.5)


def decide(user: User, approval_id: str, decision: str, feedback: str) -> dict:
    with Session.begin() as db:
        approval = db.get(Approval, approval_id)
        if not approval:
            raise DomainError("Approval not found.", 404)
        allowed = (approval.required_role == "OWNER" and user.id == approval.user_id) or (
            approval.required_role == "MANAGER"
            and user.role in {"MANAGER", "ADMIN"}
            and user.id != approval.user_id
        )
        if not allowed:
            raise DomainError("This approval requires the owner or an independent manager as indicated.", 403)
        execution = required(db, AgentExecution, approval.execution_id)
        if approval.status not in {"pending", "needs_info"} or execution.status != "awaiting_approval":
            raise DomainError("This approval is no longer waiting for a decision.", 409)
        new_status = {"approve": "approved", "reject": "rejected", "request_info": "needs_info"}[decision]
        changed = db.execute(
            update(Approval)
            .where(Approval.id == approval_id, Approval.status.in_(["pending", "needs_info"]))
            .values(status=new_status, decided_by=user.id, feedback=feedback)
        )
        if getattr(changed, "rowcount", 0) != 1:
            raise DomainError("Another reviewer already decided this request.", 409)
        if decision != "request_info":
            execution.status, execution.lease_until = "queued", 0
        db.add(
            AuditLog(
                user_id=user.id,
                action=f"approval.{decision}",
                resource_id=approval_id,
                detail={"feedback": feedback},
            )
        )
        return {"status": new_status, "execution_id": approval.execution_id}
