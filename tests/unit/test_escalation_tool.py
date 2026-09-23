from app.agent import suggest_escalation


def test_suggest_escalation_critical() -> None:
    res = suggest_escalation("EMAIL-1001")
    assert res["email_id"] == "EMAIL-1001"
    assert res["recommend_escalation"] is True
    assert "Critical" in res["reason"]
    assert "Escalate to Platform Engineering Team" in res["recommended_action"]


def test_suggest_escalation_non_critical() -> None:
    res = suggest_escalation("EMAIL-1004")
    assert res["email_id"] == "EMAIL-1004"
    assert res["recommend_escalation"] is False
    assert "Standard L1/L2" in res["recommended_action"]
