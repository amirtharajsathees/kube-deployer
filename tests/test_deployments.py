from datetime import datetime

from kubernetes.client.exceptions import ApiException

from tests.conftest import AUTH, FakeAppsApi, FakeVersionApi

KEY = "kubectl.kubernetes.io/restartedAt"
RESTART = "/api/v1/deployments/payments/api/restart"
SCALE = "/api/v1/deployments/payments/api/scale"


def test_restart_reads_then_patches_annotation_only(make_client):
    apps = FakeAppsApi()
    r = make_client(apps).post(RESTART, headers=AUTH)
    assert r.status_code == 200
    assert apps.reads == [("payments", "api")]
    assert len(apps.patches) == 1
    patch = apps.patches[0]
    annotations = patch["body"]["spec"]["template"]["metadata"]["annotations"]
    assert list(patch["body"]["spec"]) == ["template"]
    assert list(annotations) == [KEY]
    assert patch["_content_type"] == "application/strategic-merge-patch+json"
    datetime.fromisoformat(annotations[KEY])
    assert r.json() == {"namespace": "payments", "name": "api", "restarted_at": annotations[KEY]}


def test_restart_404_does_not_patch(make_client):
    apps = FakeAppsApi(read_error=ApiException(status=404))
    r = make_client(apps).post(RESTART, headers=AUTH)
    assert r.status_code == 404 and r.json() == {"detail": "Deployment not found"}
    assert apps.patches == []


def test_scale_returns_previous_and_new(make_client):
    apps = FakeAppsApi(replicas=2)
    r = make_client(apps).post(SCALE, json={"replicas": 3}, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"namespace": "payments", "name": "api", "previous_replicas": 2, "replicas": 3}
    assert apps.patches[0]["body"] == {"spec": {"replicas": 3}}


def test_scale_to_zero_allowed(make_client):
    assert make_client().post(SCALE, json={"replicas": 0}, headers=AUTH).status_code == 200


def test_scale_missing_previous_replicas_is_zero(make_client):
    r = make_client(FakeAppsApi(replicas=None)).post(SCALE, json={"replicas": 1}, headers=AUTH)
    assert r.json()["previous_replicas"] == 0


def test_scale_rejects_bad_bodies(make_client):
    c = make_client()
    assert c.post(SCALE, json={"replicas": -1}, headers=AUTH).status_code == 422
    assert c.post(SCALE, json={}, headers=AUTH).status_code == 422
    assert c.post(SCALE, json={"replicas": "3"}, headers=AUTH).status_code == 422


def test_invalid_namespace_422(make_client):
    r = make_client().post("/api/v1/deployments/BAD_NAME/api/restart", headers=AUTH)
    assert r.status_code == 422


def test_patch_error_is_502_without_upstream_body(make_client):
    err = ApiException(status=500, reason="boom")
    err.body = "SECRET-UPSTREAM-BODY"
    r = make_client(FakeAppsApi(patch_error=err)).post(RESTART, headers=AUTH)
    assert r.status_code == 502
    assert r.json() == {"detail": "Kubernetes API request failed"}
    assert "SECRET" not in r.text


def test_ready_ok_and_unreachable(make_client):
    assert make_client().get("/ready", headers=AUTH).status_code == 200
    bad = make_client(version=FakeVersionApi(error=RuntimeError("x")))
    r = bad.get("/ready", headers=AUTH)
    assert r.status_code == 503 and r.json() == {"detail": "Kubernetes API unreachable"}
    assert make_client().get("/ready").status_code == 401


def _dep(desired=3, updated=3, total=3, available=3, generation=2, observed=2):
    from types import SimpleNamespace as N

    return N(
        metadata=N(name="api", generation=generation),
        spec=N(replicas=desired),
        status=N(
            replicas=total, updated_replicas=updated, ready_replicas=available,
            available_replicas=available, observed_generation=observed,
        ),
    )


STATUS = "/api/v1/deployments/payments/api/status"


def test_rollout_status_complete(make_client):
    r = make_client(FakeAppsApi(deployment=_dep())).get(STATUS, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["rolled_out"] is True and r.json()["message"] == "Rollout complete"


def test_rollout_status_in_progress(make_client):
    c = make_client(FakeAppsApi(deployment=_dep(updated=1, total=4)))
    body = c.get(STATUS, headers=AUTH).json()
    assert body["rolled_out"] is False and body["message"] == "1 of 3 replicas updated"
    c = make_client(FakeAppsApi(deployment=_dep(generation=3)))
    assert c.get(STATUS, headers=AUTH).json()["rolled_out"] is False
    c = make_client(FakeAppsApi(deployment=_dep(available=1)))
    assert c.get(STATUS, headers=AUTH).json()["rolled_out"] is False


def test_rollout_status_404_and_auth(make_client):
    c = make_client(FakeAppsApi(read_error=ApiException(status=404)))
    assert c.get(STATUS, headers=AUTH).status_code == 404
    assert c.get(STATUS).status_code == 401


def test_list_deployments(make_client):
    r = make_client(FakeAppsApi(deployment=_dep(desired=3, available=2))).get(
        "/api/v1/deployments/payments", headers=AUTH
    )
    assert r.status_code == 200
    assert r.json() == {
        "namespace": "payments",
        "items": [{"name": "api", "namespace": "payments", "replicas": 3, "ready_replicas": 2}],
    }


def test_list_error_is_502(make_client):
    c = make_client(FakeAppsApi(read_error=ApiException(status=403)))
    assert c.get("/api/v1/deployments/payments", headers=AUTH).status_code == 502
