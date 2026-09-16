"""Measured HTTP read-load test with explicit concurrency and latency thresholds."""

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx


async def run(base, count, concurrency):
    semaphore = asyncio.Semaphore(concurrency)
    durations = []
    statuses = []
    async with httpx.AsyncClient(base_url=base, timeout=15) as client:

        async def one(index):
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(
                        ["/api/products", "/api/products/product-001", "/api/config"][index % 3]
                    )
                    statuses.append(response.status_code)
                except httpx.HTTPError:
                    statuses.append(0)
                durations.append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(count)))
        elapsed = time.perf_counter() - started
    sorted_times = sorted(durations)
    result = {
        "requests": count,
        "concurrency": concurrency,
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(count / elapsed, 2),
        "p50_ms": round(statistics.median(durations), 2),
        "p95_ms": round(sorted_times[int(0.95 * (count - 1))], 2),
        "errors": sum(s != 200 for s in statuses),
        "scope": "Local API read load; does not certify production write throughput or distributed failover.",
    }
    result["passed"] = result["errors"] == 0 and result["p95_ms"] < 1500
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8123")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    assert 1 <= args.requests <= 10000 and 1 <= args.concurrency <= 100
    result = asyncio.run(run(args.base, args.requests, args.concurrency))
    Path("verification").mkdir(exist_ok=True)
    Path("verification/load.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
