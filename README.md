# kube-deployer

A small FastAPI service that connects to **one** Kubernetes API server (details come from a config file or env vars) and exposes authenticated REST endpoints to **restart** and **scale** Deployments. It does nothing else: no create/delete, no multi-cluster, no database, no UI.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp config/config.example.yaml config/config.yaml
# edit config/config.yaml, then:
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Edit `config/config.yaml` before starting. Prefer env vars for `api_key` and `bearer_token` so secrets stay out of files. The `host`/`port` in the config document the intended bind address; the uvicorn flags are what actually bind.

## Configuration

Loaded from `config/config.yaml` (override path with `KUBE_DEPLOYER_CONFIG`), then overridden by env vars with prefix `KUBE_DEPLOYER_` and `__` between levels. A missing file is fine if env vars supply every required field. Invalid config stops startup.

| Field | Env var | Notes |
|---|---|---|
| `api.host` | `KUBE_DEPLOYER_API__HOST` | non-empty |
| `api.port` | `KUBE_DEPLOYER_API__PORT` | 1-65535 |
| `api.api_key` | `KUBE_DEPLOYER_API__API_KEY` | required; clients send it as a Bearer token |
| `kubernetes.api_server` | `KUBE_DEPLOYER_KUBERNETES__API_SERVER` | `http://` or `https://` URL |
| `kubernetes.bearer_token` | `KUBE_DEPLOYER_KUBERNETES__BEARER_TOKEN` | required; service-account token |
| `kubernetes.ca_cert_path` | `KUBE_DEPLOYER_KUBERNETES__CA_CERT_PATH` | optional; must exist if set |
| `kubernetes.verify_ssl` | `KUBE_DEPLOYER_KUBERNETES__VERIFY_SSL` | default true |
| `kubernetes.timeout_seconds` | `KUBE_DEPLOYER_KUBERNETES__TIMEOUT_SECONDS` | positive integer, default 30 |

The Kubernetes token needs `get` and `patch` on `deployments` (apps group) in the namespaces you want to manage. `~/.kube/config` and in-cluster discovery are deliberately not used.

## Usage

```bash
KEY=your-api-key

# liveness, no auth
curl http://localhost:8080/health

# readiness (calls the cluster's /version), needs auth
curl -H "Authorization: Bearer $KEY" http://localhost:8080/ready

# restart a Deployment
curl -X POST -H "Authorization: Bearer $KEY" \
  http://localhost:8080/api/v1/deployments/payments/api/restart

# list Deployments in a namespace
curl -H "Authorization: Bearer $KEY" http://localhost:8080/api/v1/deployments/payments

# check rollout status (like `kubectl rollout status`; rolled_out is true when finished)
curl -H "Authorization: Bearer $KEY" http://localhost:8080/api/v1/deployments/payments/api/status

# scale a Deployment to an absolute replica count (0 allowed)
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"replicas": 3}' \
  http://localhost:8080/api/v1/deployments/payments/api/scale
```

Restart matches `kubectl rollout restart`: it patches the pod template annotation `kubectl.kubernetes.io/restartedAt`, so pods are replaced by the normal rollout. Pods are never deleted directly.

Errors: `401` bad/missing key, `404` Deployment not found, `422` invalid input, `502` Kubernetes request failed, `503` cluster unreachable (`/ready`). Upstream error bodies, tokens and paths are never returned or logged.

## Tests

```bash
pytest
```

Tests use a fake Kubernetes client: no cluster and no `config/config.yaml` needed.
