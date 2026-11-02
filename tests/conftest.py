import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

API_KEY = "test-api-key"
AUTH = {"Authorization": f"Bearer {API_KEY}"}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("KUBE_DEPLOYER_"):
            monkeypatch.delenv(key)


class FakeAppsApi:

    def __init__(self, replicas=2, read_error=None, patch_error=None, deployment=None):
        self.deployment = deployment
        self.replicas = replicas
        self.read_error = read_error
        self.patch_error = patch_error
        self.reads, self.patches = [], []

    def read_namespaced_deployment(self, name, namespace, **kwargs):
        self.reads.append((namespace, name))
        if self.read_error:
            raise self.read_error
        return self.deployment or SimpleNamespace(
            metadata=SimpleNamespace(name=name, generation=1),
            spec=SimpleNamespace(replicas=self.replicas),
            status=SimpleNamespace(),
        )

    def list_namespaced_deployment(self, namespace, **kwargs):
        if self.read_error:
            raise self.read_error
        return SimpleNamespace(items=[self.read_namespaced_deployment("api", namespace)])

    def patch_namespaced_deployment(self, name, namespace, body, **kwargs):
        if self.patch_error:
            raise self.patch_error
        self.patches.append({"namespace": namespace, "name": name, "body": body, **kwargs})


class FakeVersionApi:
    def __init__(self, error=None):
        self.error = error

    def get_code(self, **kwargs):
        if self.error:
            raise self.error
        return object()


@pytest.fixture
def make_client():
    def _make(apps=None, version=None):
        app = create_app()
        app.state.settings = Settings.model_validate(
            {
                "api": {"api_key": API_KEY},
                "kubernetes": {"api_server": "https://k8s.example:6443", "bearer_token": "k8s-token"},
            }
        )
        app.state.apps_api = apps or FakeAppsApi()
        app.state.version_api = version or FakeVersionApi()
        return TestClient(app)  # not using "with" so the lifespan (real k8s clients) never runs

    return _make
