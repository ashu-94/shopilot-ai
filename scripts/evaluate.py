"""Small deterministic regression evaluation; not a claim of general model quality."""

import asyncio
import json
import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = (
    "sqlite:///" + (Path(tempfile.mkdtemp(prefix="shopilot-eval-")) / "eval.db").as_posix()
)

from backend.catalog import search_products
from backend.db import Base, engine
from backend.policies import approval_policy
from backend.rag import retrieve
from backend.recommendations import extract, optimize
from backend.routing import classify
from backend.seed import seed
from backend.tools import PERMISSIONS


async def main():
    Base.metadata.create_all(engine)
    seed()
    routing = [
        ("Build my home office", "shopping"),
        ("My chair arrived damaged", "support"),
        ("20 laptops for our engineering team", "procurement"),
        ("Monitor and mouse under ₹30000", "shopping"),
    ]
    routing_accuracy = sum(classify(q) == expected for q, expected in routing) / len(routing)
    retrieval = await retrieve("chair damaged return warranty", ["product-006"], support=True)
    kinds = {e["kind"] for e in retrieval["evidence"]}
    c = extract("AI/ML laptop monitor chair keyboard mouse UPS under ₹150000", "shopping")
    bundle = optimize(search_products(), c)
    result = {
        "routing_accuracy": routing_accuracy,
        "policy_compliance": approval_policy("procurement", 1000, 0)["role"] == "MANAGER",
        "retrieval_kind_recall": len(kinds & {"manual", "warranty", "return_policy", "faq"}) / 4,
        "evidence_source_validity": all(
            e["source"].startswith("catalog://product-006/") for e in retrieval["evidence"]
        ),
        "tool_selection_safety": "refund_payment" not in PERMISSIONS["search"],
        "complete_bundle_within_budget": bundle["subtotal"] <= c["budget"] and len(bundle["products"]) == 6,
    }
    print(json.dumps(result, indent=2))
    assert all(result.values()) and result["routing_accuracy"] == 1 and result["retrieval_kind_recall"] == 1


if __name__ == "__main__":
    asyncio.run(main())
