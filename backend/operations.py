from sqlalchemy import func, select

from backend.db import Session
from backend.models import (
    AgentExecution,
    AgentRun,
    Approval,
    AuditLog,
    Inventory,
    Order,
    OutboxEvent,
    Product,
)
from backend.repositories import required


def metrics() -> dict:
    with Session() as db:
        executions = db.scalars(select(AgentExecution)).all()
        calls = db.scalars(select(AuditLog).where(AuditLog.action == "mcp.call")).all()
        runs = db.scalars(select(AgentRun)).all()
        count = len(executions)
        completed = sum(e.status == "completed" for e in executions)
        failed = sum(e.status == "failed" for e in executions)
        approvals = db.scalar(select(func.count()).select_from(Approval)) or 0
        agents = []
        for agent in [
            "shopping",
            "search",
            "recommendation",
            "compatibility",
            "inventory",
            "budget",
            "order",
            "support",
            "refund",
            "procurement",
            "risk",
            "analytics",
        ]:
            subset = [r for r in runs if r.agent == agent]
            success = sum(r.status == "completed" for r in subset)
            agents.append(
                {
                    "name": agent,
                    "calls": len(subset),
                    "success_rate": round(success / len(subset) * 100, 1) if subset else None,
                    "latency_ms": round(sum(c.duration_ms for c in subset) / len(subset), 1)
                    if subset
                    else None,
                }
            )
        return {
            "total_requests": count,
            "successful": completed,
            "failed": failed,
            "average_latency_ms": round(sum(e.duration_ms for e in executions) / count, 1) if count else 0,
            "tokens": sum(e.tokens for e in executions)
            + sum(r.detail.get("inspection", {}).get("tokens", 0) for r in runs),
            "estimated_cost": sum(e.cost for e in executions)
            + sum(r.detail.get("inspection", {}).get("cost", 0) for r in runs),
            "mcp_calls": len(calls),
            "tool_failure_rate": round(
                sum(c.detail.get("outcome") == "failure" for c in calls) / len(calls) * 100, 1
            )
            if calls
            else 0,
            "human_intervention_rate": round(approvals / count * 100, 1) if count else 0,
            "agents": agents,
            "executions": [
                {
                    "id": e.id,
                    "kind": e.kind,
                    "status": e.status,
                    "duration_ms": e.duration_ms,
                    "created_at": e.created_at,
                    "trace_id": e.trace_id,
                }
                for e in sorted(executions, key=lambda e: e.created_at, reverse=True)[:20]
            ],
            "outbox_pending": db.scalar(
                select(func.count()).select_from(OutboxEvent).where(OutboxEvent.published.is_(False))
            )
            or 0,
            "dead_letters": db.scalar(
                select(func.count()).select_from(OutboxEvent).where(OutboxEvent.attempts >= 8)
            )
            or 0,
            "cache_hit_ratio": None,
            "note": "Cache and per-process latency histograms are available in Prometheus. Unused agents show no data.",
        }


def admin_summary():
    with Session() as db:
        return {
            "orders": db.scalar(select(func.count()).select_from(Order)) or 0,
            "revenue": db.scalar(
                select(func.sum(Order.total)).where(Order.status.in_(["confirmed", "delivered"]))
            )
            or 0,
            "products": db.scalar(select(func.count()).select_from(Product)) or 0,
            "low_stock": [
                {
                    "product_id": i.product_id,
                    "name": required(db, Product, i.product_id).name,
                    "stock": i.available,
                }
                for i in db.scalars(select(Inventory).where(Inventory.available < 25)).all()
            ],
            "audit": [
                {"id": a.id, "action": a.action, "resource_id": a.resource_id, "created_at": a.created_at}
                for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(40)).all()
            ],
        }
