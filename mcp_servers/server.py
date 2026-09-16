import asyncio
import json
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from backend.tools import SERVICES, invoke_tool, verify_capability


def create_server(service: str) -> FastMCP:
    if service not in SERVICES:
        raise ValueError(f"Unknown MCP service: {service}")
    server = FastMCP(
        f"ShopPilot {service}",
        host="0.0.0.0",
        port=8000,
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", f"mcp-{service}:*"],
            allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
        ),
    )

    def register(name):
        async def handler(capability: str, arguments: dict) -> str:
            claims = verify_capability(capability, name)
            result = await asyncio.to_thread(invoke_tool, claims["agent"], claims["sub"], name, arguments)
            return json.dumps(result)

        handler.__name__ = name
        handler.__doc__ = f"{name.replace('_', ' ')} using a scoped, signed ShopPilot capability. Arguments are strictly validated."
        server.tool(name=name)(handler)

    for tool in sorted(SERVICES[service]):
        register(tool)
    return server


if __name__ == "__main__":
    create_server(os.environ.get("MCP_SERVICE", "product")).run(transport="streamable-http")
