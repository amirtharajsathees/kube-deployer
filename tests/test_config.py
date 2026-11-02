import pytest
from pydantic import ValidationError

from app.config import load_settings

VALID = """
api:
  host: 0.0.0.0
  port: 8080
  api_key: file-key
kubernetes:
  api_server: https://127.0.0.1:6443
  bearer_token: file-token
  ca_cert_path: ""
  verify_ssl: true
  timeout_seconds: 30
"""


def write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return str(p)


def test_valid_yaml_loads(tmp_path):
    s = load_settings(write(tmp_path, VALID))
    assert s.api.port == 8080
    assert s.api.api_key.get_secret_value() == "file-key"
    assert s.kubernetes.api_server == "https://127.0.0.1:6443"
    assert s.kubernetes.timeout_seconds == 30


def test_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBE_DEPLOYER_KUBERNETES__BEARER_TOKEN", "env-token")
    monkeypatch.setenv("KUBE_DEPLOYER_API__API_KEY", "env-key")
    s = load_settings(write(tmp_path, VALID))
    assert s.kubernetes.bearer_token.get_secret_value() == "env-token"
    assert s.api.api_key.get_secret_value() == "env-key"


def test_config_path_from_env_and_env_only(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBE_DEPLOYER_CONFIG", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("KUBE_DEPLOYER_API__API_KEY", "k")
    monkeypatch.setenv("KUBE_DEPLOYER_KUBERNETES__API_SERVER", "http://localhost:8001")
    monkeypatch.setenv("KUBE_DEPLOYER_KUBERNETES__BEARER_TOKEN", "t")
    assert load_settings().kubernetes.api_server == "http://localhost:8001"


def test_missing_file_and_no_env_fails(tmp_path):
    with pytest.raises(ValidationError):
        load_settings(str(tmp_path / "nope.yaml"))


def test_empty_token_fails(tmp_path):
    with pytest.raises(ValidationError):
        load_settings(write(tmp_path, VALID.replace("file-token", '""')))


def test_bad_api_server_fails(tmp_path):
    with pytest.raises(ValidationError):
        load_settings(write(tmp_path, VALID.replace("https://127.0.0.1:6443", "ftp://nope")))


def test_missing_ca_file_fails(tmp_path):
    with pytest.raises(ValidationError):
        load_settings(write(tmp_path, VALID.replace('ca_cert_path: ""', "ca_cert_path: /no/such/ca.pem")))
