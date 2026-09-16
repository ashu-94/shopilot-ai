"""Review aggregates expose sample size and evidence, never claim fraud certainty."""

import re
from collections import Counter

ASPECTS = {
    "battery": {"battery", "charging", "charge"},
    "performance": {"fast", "slow", "performance", "ram", "speed"},
    "comfort": {"comfort", "comfortable", "ergonomic", "back"},
    "durability": {"broken", "broke", "durable", "quality", "damage"},
    "noise": {"noise", "noisy", "quiet", "fan"},
    "delivery": {"delivery", "arrived", "packaging", "shipping"},
}


def analyze(reviews: list[dict]) -> dict:
    texts = [re.sub(r"\W+", " ", str(r.get("text", "")).lower()).strip() for r in reviews]
    counts = Counter(texts)
    aspects = {}
    for aspect, words in ASPECTS.items():
        matches = [r for r, text in zip(reviews, texts, strict=True) if words.intersection(text.split())]
        if matches:
            aspects[aspect] = {
                "mentions": len(matches),
                "average_rating": round(sum(r["rating"] for r in matches) / len(matches), 2),
                "evidence": [{"id": r.get("id"), "excerpt": r["text"][:250]} for r in matches[:3]],
            }
    total = len(reviews)
    distribution = {str(n): sum(r["rating"] == n for r in reviews) for n in range(1, 6)}
    return {
        "sample_size": total,
        "verified_count": sum(bool(r.get("verified")) for r in reviews),
        "rating_distribution": distribution,
        "aspects": aspects,
        "duplicate_text_count": sum(n - 1 for text, n in counts.items() if text),
        "confidence": "low" if total < 20 else "moderate",
        "limitations": [
            "Small or synthetic samples do not establish real-world quality.",
            "Duplicate text is a review-quality signal, not a fraud finding.",
        ],
    }
