import asyncio
import json
import time
from contextvars import ContextVar
from typing import Any

import jwt
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import Field

from backend import catalog, commerce
from backend.config import settings
from backend.db import Session
from backend.errors import DomainError
from backend.models import AuditLog, Inventory, User
from backend.observability import MCP_CALLS, MCP_LATENCY
from backend.repositories import required
from backend.schemas import StrictModel

active_agent: ContextVar[str | None] = ContextVar("active_agent", default=None)

SERVICES = {
    "product": {
        "search_products",
        "get_product",
        "compare_products",
        "get_product_specs",
        "get_product_reviews",
    },
    "inventory": {"check_inventory", "reserve_inventory", "release_inventory"},
    "order": {"create_order", "get_order", "cancel_order", "get_order_history"},
    "payment": {"create_payment", "verify_payment", "refund_payment"},
    "shipping": {"calculate_shipping", "create_shipment", "track_shipment"},
    "customer": {"get_customer", "get_preferences", "get_customer_orders"},
    "coupon": {"validate_coupon", "find_best_coupon", "apply_coupon"},
}
PERMISSIONS = {
    "shopping": {"get_preferences", "search_products"},
    "search": {"search_products", "get_product", "get_product_specs"},
    "recommendation": {"get_product", "get_product_reviews", "compare_products"},
    "compatibility": {"get_product_specs", "compare_products"},
    "budget": {"find_best_coupon", "validate_coupon", "apply_coupon"},
    "inventory": {"check_inventory"},
    "order": {
        "create_order",
        "get_order",
        "get_order_history",
        "cancel_order",
        "reserve_inventory",
        "release_inventory",
        "create_payment",
        "verify_payment",
        "create_shipment",
        "track_shipment",
        "calculate_shipping",
    },
    "support": {"get_customer_orders", "get_product", "get_product_specs", "get_order", "track_shipment"},
    "refund": {"get_order", "refund_payment"},
    "procurement": {"search_products", "compare_products", "check_inventory", "find_best_coupon"},
    "risk": {"get_customer_orders"},
    "analytics": set(),
}


class ToolArgs(StrictModel):
    query: str = Field(default="", max_length=3000)
    category: str = Field(default="", max_length=40)
    max_price: int = Field(default=10000000, ge=1, le=100000000)
    product_id: str = Field(default="", max_length=64)
    product_ids: list[str] = Field(default_factory=list, max_length=40)
    order_id: str = Field(default="", max_length=64)
    execution_id: str = Field(default="", max_length=64)
    subtotal: int = Field(default=0, ge=0, le=100000000)
    code: str | None = Field(default=None, max_length=32)


def service_for(tool: str) -> str:
    for service, names in SERVICES.items():
        if tool in names:
            return service
    raise DomainError("Unknown tool.", 400)


def invoke_tool(agent: str, user_id: str, name: str, arguments: dict) -> Any:
    if name not in PERMISSIONS.get(agent, set()):
        raise DomainError("Agent is not authorized for this tool.", 403, "tool_forbidden")
    args = ToolArgs.model_validate(arguments)
    with Session() as db:
        if not required(db, User, user_id):
            raise DomainError("Invalid tool principal.", 403)
    if name == "search_products":
        return catalog.search_products(args.query, args.category, args.max_price)
    if name in {"get_product", "get_product_specs"}:
        return catalog.get_product(args.product_id)
    if name == "compare_products":
        return [catalog.get_product(pid) for pid in args.product_ids]
    if name == "get_product_reviews":
        return catalog.reviews(args.product_id)
    if name == "check_inventory":
        with Session() as db:
            row = required(db, Inventory, args.product_id)
            if not row:
                raise DomainError("Inventory not found.", 404)
            return {"product_id": args.product_id, "available": row.available, "version": row.version}
    if name in {"find_best_coupon", "validate_coupon", "apply_coupon"}:
        with Session() as db:
            return catalog.coupon_for(db, args.subtotal, args.code)
    if name == "create_order":
        return commerce.create_order(user_id, args.execution_id)
    if name == "cancel_order" or name == "release_inventory":
        return commerce.cancel_order(user_id, args.execution_id)
    if name in {"get_order_history", "get_customer_orders"}:
        return commerce.history(user_id)
    if name in {"get_customer", "get_preferences"}:
        return commerce.customer(user_id)
    if name == "refund_payment":
        return commerce.resolve_return(user_id, args.execution_id)
    if name in {"reserve_inventory", "create_payment", "create_shipment"}:
        # One atomic mock transaction owns reservation, settlement and initial shipment.
        # These ensure operations are idempotent views over that same approved transaction.
        order = commerce.create_order(user_id, args.execution_id)
        return (
            order["payment"]
            if name == "create_payment"
            else order["shipments"]
            if name == "create_shipment"
            else order["items"]
        )
    if name in {"get_order", "verify_payment", "track_shipment"}:
        order = commerce.get_order(user_id, args.order_id)
        return (
            order["payment"]
            if name == "verify_payment"
            else order["shipments"]
            if name == "track_shipment"
            else order
        )
    if name == "calculate_shipping":
        products = [catalog.get_product(pid) for pid in args.product_ids]
        return {
            "amount": 0,
            "estimated_days": max((p["delivery_days"] for p in products), default=7),
            "simulated": True,
        }
    raise DomainError("Tool not implemented.", 400)


def capability_token(agent: str, user_id: str, tool: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "agent": agent,
            "tool": tool,
            "type": "mcp_capability",
            "aud": "shopilot-mcp",
            "exp": time.time() + 60,
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


def verify_capability(token: str, name: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings().jwt_secret,
            algorithms=["HS256"],
            audience="shopilot-mcp",
            options={"require": ["sub", "exp", "agent", "tool", "type"]},
        )
        if claims["tool"] != name or claims["type"] != "mcp_capability":
            raise jwt.InvalidTokenError()
        return claims
    except jwt.PyJWTError:
        raise DomainError("Invalid tool capability.", 403) from None


async def call(agent: str, user_id: str, tool: str, **arguments):
    if active_agent.get() is not None and active_agent.get() != agent:
        raise DomainError("Specialist cannot impersonate another agent.", 403, "tool_forbidden")
    if tool not in PERMISSIONS.get(agent, set()):
        raise DomainError("Agent is not authorized for this tool.", 403, "tool_forbidden")
    started = time.perf_counter()
    outcome = "success"
    try:
        if settings().mcp_transport == "inprocess":
            result = await asyncio.to_thread(invoke_tool, agent, user_id, tool, arguments)
        else:
            service = service_for(tool)
            url = f"http://{settings().mcp_host}-{service}:8000/mcp"
            async with asyncio.timeout(20):
                async with streamablehttp_client(url) as (read, write, _):
                    async with ClientSession(read, write) as client:
                        await client.initialize()
                        response = await client.call_tool(
                            tool,
                            {"capability": capability_token(agent, user_id, tool), "arguments": arguments},
                        )
                        if response.isError:
                            raise DomainError("MCP tool rejected the operation.", 502, "mcp_error")
                        content = response.content[0]
                        if content.type != "text":
                            raise DomainError("Unexpected MCP response type", 502)
                        result = json.loads(content.text)
        return result
    except Exception:
        outcome = "failure"
        raise
    finally:
        elapsed = time.perf_counter() - started
        MCP_CALLS.labels(agent, tool, outcome).inc()
        MCP_LATENCY.labels(tool).observe(elapsed)
        with Session.begin() as db:
            db.add(
                AuditLog(
                    user_id=user_id,
                    action="mcp.call",
                    resource_id=tool,
                    detail={"agent": agent, "outcome": outcome, "duration_ms": round(elapsed * 1000, 2)},
                )
            )
