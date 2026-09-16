import asyncio
import json
import os
import subprocess
import sys

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from sqlalchemy import select

from backend.db import Base, Session, engine
from backend.models import User
from backend.seed import seed
from backend.tools import SERVICES, capability_token, verify_capability
from mcp_servers.server import create_server


async def test_all_seven_servers_register_their_tools():
    for service, names in SERVICES.items():
        listed = await create_server(service).list_tools()
        assert {t.name for t in listed} == names


def test_capability_cannot_be_reused_for_another_tool():
    from backend.errors import DomainError

    token = capability_token("search", "fake-user", "search_products")
    with pytest.raises(DomainError):
        verify_capability(token, "refund_payment")


async def test_official_mcp_streamable_http_roundtrip():
    Base.metadata.create_all(engine)
    seed()
    with Session() as db:
        user = db.scalar(select(User))
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from mcp_servers.server import create_server; s=create_server('product'); s.settings.port=8107; s.run(transport='streamable-http')",
        ],
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        async with httpx.AsyncClient() as http:
            for _ in range(80):
                try:
                    await http.get("http://127.0.0.1:8107/mcp", timeout=0.5)
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(0.1)
            else:
                raise AssertionError("MCP test server did not start")
        async with streamablehttp_client("http://127.0.0.1:8107/mcp") as (read, write, _):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.call_tool(
                    "search_products",
                    {
                        "capability": capability_token("search", user.id, "search_products"),
                        "arguments": {"category": "laptop"},
                    },
                )
                assert not result.isError, result
                products = json.loads(result.content[0].text)
                assert len(products) == 3
                assert all(p["category"] == "laptop" for p in products)
    finally:
        process.terminate()
        process.wait(timeout=10)
