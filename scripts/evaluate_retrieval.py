"""A small, versioned held-out paraphrase suite for the local retrieval models."""

import json
import time
from pathlib import Path

from backend.config import settings
from backend.semantic import embedding, query_embedding, rerank

CASES = [
    ("backup power during an outage", "The UPS provides battery backup when mains electricity fails."),
    (
        "comfortable seat for long work sessions",
        "An ergonomic office chair provides adjustable lumbar support.",
    ),
    ("carry my computer on a daily commute", "This lightweight portable laptop weighs just 1.3 kilograms."),
    (
        "keep running containers without running out of memory",
        "A workstation with 64 GB RAM supports concurrent Docker workloads.",
    ),
    (
        "screen that connects using a reversible cable",
        "The monitor has a USB-C input for display connectivity.",
    ),
    ("type without waking someone", "This keyboard uses quiet low-noise switches."),
    ("avoid tangled cables on my desk", "The wireless mouse connects over Bluetooth."),
    ("listen without hearing the room around me", "These headphones provide active noise cancellation."),
    (
        "replace a purchase that arrived broken",
        "Damaged deliveries qualify for a reviewed replacement under the return policy.",
    ),
    ("how long will defects be covered", "The manufacturer warranty covers faults for thirty-six months."),
    (
        "fit many development projects on disk",
        "The laptop includes a one terabyte solid-state storage drive.",
    ),
    (
        "speak clearly during remote meetings",
        "The webcam microphone captures clear speech during video calls.",
    ),
    ("change between sitting and standing", "This height-adjustable desk supports standing work."),
    (
        "connect a display with high refresh rate",
        "The monitor supports a 144 Hz refresh rate over DisplayPort.",
    ),
    ("save money on a complete purchase", "A valid coupon reduces the total cart price."),
    ("when will the parcel arrive", "Estimated shipping delivery is five business days."),
    (
        "return just one item from several purchased",
        "Select the product quantity for a partial refund; other items stay on the order.",
    ),
    (
        "who must authorize the team purchase",
        "Business procurement requires an independent manager approval.",
    ),
    (
        "what happens if the charge fails",
        "A declined mock payment rolls back inventory and does not create an order.",
    ),
    (
        "avoid paying twice after retrying",
        "The idempotency key ensures repeated checkout creates only one payment.",
    ),
    ("fan sounds distracting while I work", "Reviews report noticeable cooling noise under heavy CPU load."),
    (
        "can this drive demanding local language models",
        "GPU memory and model size determine local language model capacity.",
    ),
    (
        "prove where the recommendation came from",
        "Each recommendation links to catalog specifications, reviews and policy evidence.",
    ),
    (
        "recover a request after a server interruption",
        "Durable graph checkpoints resume pending workflows after restart.",
    ),
]

if __name__ == "__main__":
    started = time.perf_counter()
    docs = [{"text": text, "id": str(index)} for index, (_, text) in enumerate(CASES)]
    vectors = [embedding(d["text"]) for d in docs]
    records = []
    for index, (query, _) in enumerate(CASES):
        vector = query_embedding(query)
        ranked = sorted(
            zip(docs, vectors),
            key=lambda pair: sum(a * b for a, b in zip(vector, pair[1], strict=True)),
            reverse=True,
        )
        candidates = [pair[0] for pair in ranked[:8]]
        final = rerank(query, candidates)
        ids = [d["id"] for d in final]
        rank = ids.index(str(index)) + 1 if str(index) in ids else None
        records.append({"query": query, "rank": rank, "top_id": ids[0]})
    mrr = sum(1 / r["rank"] if r["rank"] else 0 for r in records) / len(records)
    recall = sum(r["rank"] is not None and r["rank"] <= 3 for r in records) / len(records)
    result = {
        "cases": len(CASES),
        "embedding_model": settings().embedding_model,
        "reranker_model": settings().reranker_model,
        "mrr_at_8": round(mrr, 4),
        "recall_at_3": round(recall, 4),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "passed": mrr >= 0.85 and recall >= 0.9,
        "records": records,
        "limits": "Authored English paraphrase regression set, not independent production relevance or fraud validation.",
    }
    Path("verification").mkdir(exist_ok=True)
    Path("verification/retrieval.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
