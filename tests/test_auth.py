from tests.conftest import AUTH

URL = "/api/v1/deployments/payments/api/restart"


def test_health_needs_no_header(make_client):
    r = make_client().get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_missing_header_401(make_client):
    r = make_client().post(URL)
    assert r.status_code == 401 and r.json() == {"detail": "Unauthorized"}


def test_wrong_token_and_scheme_401(make_client):
    c = make_client()
    assert c.post(URL, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.post(URL, headers={"Authorization": "Basic test-api-key"}).status_code == 401


def test_correct_token_reaches_handler(make_client):
    assert make_client().post(URL, headers=AUTH).status_code == 200
