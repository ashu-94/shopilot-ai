import hashlib
import json
import re
import time

from backend.config import settings
from backend.errors import DomainError


def fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def input_guard(query: str) -> None:
    patterns = [
        r"ignore\s+(all\s+)?(previous|system)\s+instructions",
        r"(reveal|print|show|leak).{0,25}(secret|api.key|system.prompt)",
        r"(bypass|disable).{0,20}(approval|guardrail|authorization)",
        r"(execute|run).{0,10}(shell|sql|command)",
    ]
    if any(re.search(p, query, re.I) for p in patterns):
        raise DomainError(
            "This request contains unsupported tool or security instructions.", 400, "input_guardrail"
        )
    if len(query.strip()) < 8:
        raise DomainError("Describe your goal in a little more detail.")


def risk(
    amount: int,
    account_created: float,
    refunds: int = 0,
    failed_payments: int = 0,
    shipping_anomaly: bool = False,
) -> dict:
    score, reasons = 0, []
    for applies, points, reason in [
        (amount >= settings().approval_threshold, 30, "High-value transaction"),
        (time.time() - account_created < 7 * 86400, 10, "New account"),
        (refunds >= 3, 35, "Repeated refunds"),
        (failed_payments >= 3, 30, "Repeated failed payments"),
        (shipping_anomaly, 40, "Shipping anomaly"),
    ]:
        if applies:
            score += points
            reasons.append(reason)
    score = min(score, 100)
    return {
        "score": score,
        "level": "high" if score >= 65 else "medium" if score >= 30 else "low",
        "reasons": reasons,
        "recommended_action": "human_review" if score >= 65 else "continue",
    }


def approval_policy(kind: str, amount: int, risk_score: int, discount_percent: float = 0) -> dict:
    if kind == "procurement":
        return {"role": "MANAGER", "reason": "Business purchase orders require manager approval."}
    if kind == "return" and amount > settings().refund_approval_threshold:
        return {"role": "MANAGER", "reason": "Return value exceeds the configured review threshold."}
    if risk_score >= 65 or discount_percent > 20:
        return {"role": "MANAGER", "reason": "Risk or discount policy requires independent review."}
    return {"role": "OWNER", "reason": "Confirm the exact items and amount before simulated payment."}
