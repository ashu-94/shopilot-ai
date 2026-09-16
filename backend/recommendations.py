import re

from backend.errors import DomainError

CATEGORIES = {
    "laptop": ["laptop", "notebook"],
    "monitor": ["monitor", "display"],
    "chair": ["chair"],
    "keyboard": ["keyboard"],
    "mouse": ["mouse"],
    "ups": ["ups", "backup power"],
    "desk": ["desk"],
    "headphones": ["headphone", "headset"],
    "tv": ["tv", "television"],
    "soundbar": ["soundbar"],
    "appliance": ["refrigerator", "washer", "appliance"],
    "webcam": ["webcam"],
}


def extract(query: str, mode: str, budget_override: int | None = None) -> dict:
    q = query.lower().replace(",", "")
    if re.search(r"\b(macbook|apple|dell|lenovo|asus|acer|samsung|flipkart|amazon)\b", q):
        raise DomainError(
            "This local demo contains fictional brands only. It cannot verify live marketplace prices or real-brand specifications. Try 'laptop for Python and Docker under ₹100000' to explore the synthetic catalog.",
            409,
            "unsupported_catalog",
        )
    categories = [key for key, words in CATEGORIES.items() if any(word in q for word in words)]
    if not categories and ("office" in q or "workspace" in q):
        categories = ["laptop", "monitor", "chair", "keyboard", "mouse", "ups"]
    if not categories:
        raise DomainError(
            "I couldn't match this goal to the demo catalog. Try a workspace, laptop, or home entertainment setup."
        )
    amount = re.search(r"(?:₹|rs\.?\s*|inr\s*|under\s+|budget\s+)(\d+(?:\.\d+)?)\s*(lakh|lac|k|million)?", q)
    budget = budget_override or (
        int(
            float(amount[1])
            * {"lakh": 100000, "lac": 100000, "k": 1000, "million": 1000000}.get(amount[2], 1)
        )
        if amount
        else (2500000 if mode == "procurement" else 150000)
    )
    count = re.search(r"(\d+)\s+(?:engineering\s+)?laptops?", q)
    ram = re.search(r"(\d+)\s*gb\s*(?:of\s*)?(?:ram|memory)", q)
    ssd = re.search(r"(\d+)\s*(tb|gb)\s*(?:ssd|storage)", q)
    technical = any(word in q for word in ["llm", "ai/ml", "docker", "ai engineering"])
    return {
        "budget": budget,
        "categories": categories,
        "quantity": int(count[1]) if count else 1,
        "min_ram_gb": int(ram[1]) if ram else 32 if technical else 0,
        "min_ssd_gb": int(ssd[1]) * (1024 if ssd[2] == "tb" else 1) if ssd else 1024 if technical else 0,
        "min_warranty_months": 36 if any(t in q for t in ["three-year", "three year", "3-year"]) else 0,
        "max_delivery_days": 14 if any(t in q for t in ["two weeks", "2 weeks"]) else 30,
        "local_llm": "llm" in q or "ai/ml" in q,
        "mode": mode,
    }


def rank(product: dict, constraints: dict, preferences: dict | None = None) -> float:
    rating = product["rating"] / 5
    warranty = min(product["warranty_months"] / 36, 1)
    memory = min(product["specs"].get("ram_gb", 32) / 64, 1)
    preference = 1 if product["category"] in (preferences or {}).get("preferred_categories", []) else 0
    return round(
        0.55 * rating
        + 0.15 * warranty
        + 0.15 * memory
        + 0.1 * min(product["stock"] / 20, 1)
        + 0.05 * preference,
        4,
    )


def optimize(products: list[dict], constraints: dict, preferences: dict | None = None) -> dict:
    quantity = constraints["quantity"]
    states: list[tuple[int, float, list[dict]]] = [(0, 0.0, [])]
    cheapest = []
    for category in constraints["categories"]:
        candidates = [
            p
            for p in products
            if p["category"] == category
            and p["stock"] >= quantity
            and p["delivery_days"] <= constraints["max_delivery_days"]
            and (
                category != "laptop"
                or (
                    p["specs"].get("ram_gb", 0) >= constraints["min_ram_gb"]
                    and p["specs"].get("ssd_gb", 0) >= constraints["min_ssd_gb"]
                    and p["warranty_months"] >= constraints["min_warranty_months"]
                )
            )
        ]
        if not candidates:
            raise DomainError(
                f"No {category} meets the required specifications, delivery and quantity. Try changing the requirements.",
                409,
            )
        cheapest.append(min(candidates, key=lambda p: p["price"]))
        expanded = [
            (cost + p["price"] * quantity, score + rank(p, constraints, preferences), bundle + [p])
            for cost, score, bundle in states
            for p in candidates
            if cost + p["price"] * quantity <= constraints["budget"]
        ]
        if not expanded:
            raise DomainError(
                "The complete bundle cannot fit the budget. Increase the budget or remove a requirement.",
                409,
                "budget_infeasible",
            )
        # Exact Pareto frontier for this small catalog; no budget rounding.
        states, best_score = [], -1.0
        for candidate in sorted(expanded, key=lambda s: (s[0], -s[1])):
            if candidate[1] > best_score:
                states.append(candidate)
                best_score = candidate[1]
    cost, score, selected = max(states, key=lambda s: (s[1], -s[0]))
    return {
        "products": selected,
        "subtotal": cost,
        "score": round(score, 3),
        "alternative": {"products": cheapest, "subtotal": sum(p["price"] * quantity for p in cheapest)},
        "quantity": quantity,
    }


def compatibility(products: list[dict], constraints: dict) -> list[str]:
    by_category = {p["category"]: p for p in products}
    warnings = []
    laptop, monitor, ups = (by_category.get(k) for k in ["laptop", "monitor", "ups"])
    if (
        laptop
        and monitor
        and not set(laptop["specs"].get("ports", [])) & set(monitor["specs"].get("ports", []))
    ):
        warnings.append("The laptop and monitor need a display adapter; its cost is not included.")
    if (
        ups
        and sum(p["specs"].get("power_w", 0) for p in products if p != ups) * 1.25 > ups["specs"]["output_w"]
    ):
        warnings.append("The UPS has insufficient headroom for the listed peak power requirements.")
    if laptop and constraints["local_llm"]:
        warnings.append(
            "Local model capacity depends on model size and quantization. This configuration suits smaller models; large-model training is not guaranteed."
        )
    if "chair" in by_category and "desk" in by_category:
        warnings.append(
            "Confirm chair arm clearance and your room dimensions before purchase; desk width alone does not establish fit."
        )
    return warnings
