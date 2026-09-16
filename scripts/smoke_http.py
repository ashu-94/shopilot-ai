"""Run a shopping mission through a running API, including distributed MCP in Compose."""

import json
import time
import urllib.request

BASE = "http://localhost:8000/api"


def request(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode() if body else None, headers=headers
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


login = request("/auth/login", {"email": "alex@shopilot.demo", "password": "ShopPilot-demo-2026!"})
token = login["access_token"]
mission = request(
    "/missions", {"query": "AI/ML laptop monitor chair keyboard mouse UPS under ₹150000"}, token
)
for attempt in range(120):
    result = request(f"/executions/{mission['id']}", token=token)
    if result["status"] in {"completed", "failed"}:
        assert result["status"] == "completed", result
        assert len(result["result"]["products"]) == 6 and result["result"]["total"] <= 150000
        print("Distributed shopping smoke test passed")
        break
    time.sleep(0.5)
else:
    raise SystemExit("Workflow timed out")
