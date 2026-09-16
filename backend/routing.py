import re


def classify(query: str, requested_mode: str = "shopping") -> str:
    """Fast deterministic routing; financial execution still requires a structured request."""
    if requested_mode != "shopping":
        return requested_mode
    lowered = query.lower()
    if re.search(r"\b(damaged|refund|replacement|return my|strange noise|not working|broken)\b", lowered):
        return "support"
    if (
        "procurement" in lowered
        or re.search(r"\b(?:team|company|business)\b", lowered)
        and re.search(r"\b\d+\s+(?:engineering\s+)?laptops?\b", lowered)
    ):
        return "procurement"
    return "shopping"
