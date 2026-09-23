from app.agent import search_failed_emails, get_email_error_detail


def test_search_failed_emails() -> None:
    res = search_failed_emails()
    assert res["count"] == 7
    email_ids = [e["email_id"] for e in res["failed_emails"]]
    assert "EMAIL-1001" in email_ids
    assert "EMAIL-1010" in email_ids


def test_get_email_error_detail() -> None:
    res = get_email_error_detail("EMAIL-1001")
    assert res["email_id"] == "EMAIL-1001"
    assert res["severity"] == "Critical"
    assert "Invoice-Intake-Flow" in res["flow_name"]
