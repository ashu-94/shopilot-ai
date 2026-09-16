"""Local ONNX inference; no customer data leaves the process."""

import hashlib
from functools import lru_cache

import numpy as np

from backend.config import settings


@lru_cache(maxsize=1)
def encoder():
    from fastembed import TextEmbedding

    return TextEmbedding(
        model_name=settings().embedding_model, cache_dir=settings().model_cache_dir, threads=2
    )


@lru_cache(maxsize=1)
def reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    return TextCrossEncoder(
        model_name=settings().reranker_model, cache_dir=settings().model_cache_dir, threads=2
    )


def collection_name():
    identity = f"{settings().retrieval_backend}:{settings().embedding_model}:v1"
    return "shopilot_knowledge_" + hashlib.sha256(identity.encode()).hexdigest()[:12]


@lru_cache(maxsize=4096)
def embedding(text: str) -> tuple[float, ...]:
    vector = next(iter(encoder().embed([text])))
    vector = np.asarray(vector, dtype=np.float32)
    vector /= max(float(np.linalg.norm(vector)), 1e-12)
    return tuple(float(x) for x in vector)


def rerank(query: str, docs: list[dict]) -> list[dict]:
    if not docs:
        return []
    scores = list(reranker().rerank(query, [d["text"] for d in docs], batch_size=16))
    return sorted(
        [{**doc, "rerank_score": float(score)} for doc, score in zip(docs, scores, strict=True)],
        key=lambda d: d["rerank_score"],
        reverse=True,
    )


@lru_cache(maxsize=1024)
def query_embedding(text: str) -> tuple[float, ...]:
    vector = np.asarray(next(iter(encoder().query_embed(text))), dtype=np.float32)
    vector /= max(float(np.linalg.norm(vector)), 1e-12)
    return tuple(float(x) for x in vector)
