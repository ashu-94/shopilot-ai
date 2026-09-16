from backend.policies import risk
from backend.routing import classify


def test_supervisor_routes_support_and_team_purchases():
    assert classify("My refrigerator makes a strange noise") == "support"
    assert classify("We need 20 laptops for our team") == "procurement"
    assert classify("Monitor under ₹20000") == "shopping"


def test_combined_risk_signals_require_review():
    result = risk(150000, 0, refunds=3, failed_payments=3, shipping_anomaly=True)
    assert result["score"] == 100
    assert result["recommended_action"] == "human_review"
