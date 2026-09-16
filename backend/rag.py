import asyncio
import hashlib
import math
import re
import time
from collections import Counter

from qdrant_client import QdrantClient, models
from sqlalchemy import select

from backend import semantic
from backend.config import settings
from backend.db import Session
from backend.models import KnowledgeDocument
from backend.observability import RETRIEVAL

DIMENSION = 256


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def embed(text: str) -> list[float]:
    if settings().retrieval_backend == "learned":
        return list(semantic.embedding(text))
    # Deterministic signed feature hashing: reproducible, offline baseline.
    # This is a lexical vector embedding, not a learned semantic model.
    vector = [0.0] * DIMENSION
    for token, count in Counter(tokens(text)).items():
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % DIMENSION
        vector[index] += (1 if digest[4] & 1 else -1) * (1 + math.log(count))
    norm = math.sqrt(sum(v * v for v in vector)) or 1
    return [v / norm for v in vector]


def query_plan(query: str, support=False) -> dict:
    rewritten = (
        query.lower()
        .replace("llm", "local language model ram gpu memory")
        .replace("docker", "docker ram cpu")
    )
    return {
        "query": rewritten,
        "kinds": ["manual", "warranty", "return_policy", "faq"]
        if support
        else ["description", "specifications", "review", "warranty", "return_policy"],
    }


def documents(kind: str, product_ids: list[str]) -> list[dict]:
    with Session() as db:
        rows = db.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.kind == kind, KnowledgeDocument.product_id.in_(product_ids)
            )
        ).all()
        return [
            {
                "id": d.id,
                "product_id": d.product_id,
                "kind": d.kind,
                "title": d.title,
                "text": d.text,
                "source": d.source,
            }
            for d in rows
        ]


def ingest() -> int:
    if not settings().qdrant_url:
        return 0
    client = QdrantClient(url=settings().qdrant_url, timeout=5)
    if not client.collection_exists(semantic.collection_name()):
        client.create_collection(
            semantic.collection_name(),
            vectors_config=models.VectorParams(
                size=len(embed("dimension probe")), distance=models.Distance.COSINE
            ),
        )
    with Session() as db:
        docs = db.scalars(select(KnowledgeDocument)).all()
        points = [
            models.PointStruct(
                id=d.id,
                vector=embed(d.text),
                payload={
                    "product_id": d.product_id,
                    "kind": d.kind,
                    "source": d.source,
                    "text": d.text,
                    "title": d.title,
                },
            )
            for d in docs
        ]
    client.upsert(semantic.collection_name(), points=points, wait=True)
    client.close()
    return len(points)


def vector_scores(query: str, product_ids: list[str], kinds: list[str]) -> dict:
    if not settings().qdrant_url:
        return {}
    try:
        client = QdrantClient(url=settings().qdrant_url, timeout=3)
        result = client.query_points(
            semantic.collection_name(),
            query=list(semantic.query_embedding(query))
            if settings().retrieval_backend == "learned"
            else embed(query),
            limit=50,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="product_id", match=models.MatchAny(any=product_ids)),
                    models.FieldCondition(key="kind", match=models.MatchAny(any=kinds)),
                ]
            ),
        )
        return {str(p.id).replace("-", ""): p.score for p in result.points}
    except Exception:
        return {}  # SQL evidence remains authoritative and available.


async def retrieve(query: str, product_ids: list[str], support=False) -> dict:
    started = time.perf_counter()
    plan = query_plan(query, support)
    groups = await asyncio.gather(
        *(asyncio.to_thread(documents, kind, product_ids) for kind in plan["kinds"])
    )
    docs = [d for group in groups for d in group]
    external = await asyncio.to_thread(vector_scores, plan["query"], product_ids, plan["kinds"])
    query_tokens = set(tokens(plan["query"]))
    vector = await asyncio.to_thread(
        semantic.query_embedding if settings().retrieval_backend == "learned" else embed, plan["query"]
    )
    doc_vectors = await asyncio.to_thread(lambda: [embed(d["text"]) for d in docs])
    for doc, doc_vector in zip(docs, doc_vectors, strict=True):
        words = tokens(doc["text"])
        lexical = sum(math.log(1 + words.count(t)) for t in query_tokens) / max(1, math.sqrt(len(words)))
        cosine = external.get(doc["id"], sum(a * b for a, b in zip(vector, doc_vector, strict=True)))
        doc["score"] = round(0.65 * lexical + 0.35 * max(0, cosine), 4)
    # Diversify by product and kind so warranties do not disappear behind long descriptions.
    ranked = sorted(docs, key=lambda d: d["score"], reverse=True)
    if settings().retrieval_backend == "learned":
        ranked = await asyncio.to_thread(semantic.rerank, plan["query"], ranked[:80])
    evidence, seen = [], set()
    for doc in ranked:
        key = (doc["product_id"], doc["kind"])
        if key not in seen and doc["source"].startswith(f"catalog://{doc['product_id']}/"):
            evidence.append({**doc, "text": doc["text"][:600]})
            seen.add(key)
    elapsed = time.perf_counter() - started
    RETRIEVAL.observe(elapsed)
    return {
        "plan": plan,
        "evidence": evidence[:80],
        "latency_ms": round(elapsed * 1000, 2),
        "retrieval_mode": "qdrant_hybrid"
        if external
        else "sql_learned_hybrid"
        if settings().retrieval_backend == "learned"
        else "sql_hybrid_baseline",
        "embedding_model": settings().embedding_model
        if settings().retrieval_backend == "learned"
        else "feature_hash",
        "reranker": settings().reranker_model if settings().retrieval_backend == "learned" else "lexical",
        "vector_store_available": bool(external),
        "grounded": bool(evidence),
    }
