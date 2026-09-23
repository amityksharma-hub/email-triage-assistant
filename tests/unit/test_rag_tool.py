from app.agent import consult_error_reference


def test_consult_error_reference_err_401() -> None:
    res = consult_error_reference("ERR-401")
    assert res["error_code"] == "ERR-401"
    assert "Authentication failure" in res["description"]
    assert "expired service account credential" in res["common_cause"]
    assert "Power Platform" in res["remediation"]


def test_consult_error_reference_err_502() -> None:
    res = consult_error_reference("ERR-502")
    assert res["error_code"] == "ERR-502"
    assert "Attachment size exceeded" in res["description"]
    assert "25MB" in res["common_cause"]


def test_consult_error_reference_numeric_code() -> None:
    res = consult_error_reference("504")
    assert res["error_code"] == "ERR-504"
    assert "Gateway timeout" in res["description"]
