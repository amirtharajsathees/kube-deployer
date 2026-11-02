KUBE-DEPLOYER - QUICK START
===========================

WHAT IT IS
  A small Python web service that restarts or scales Kubernetes Deployments
  through a REST API. It talks to one cluster, using the API server URL and
  token you put in a config file. See README.md for more detail.

REQUIREMENTS
  Python 3.11 or newer.
  A Kubernetes API server URL and a bearer token (e.g. a service account
  token) allowed to "get" and "patch" Deployments.

1) INSTALL
     python -m venv .venv
     source .venv/bin/activate          (Windows: .venv\Scripts\activate)
     pip install -e ".[dev]"

2) CONFIGURE
     cp config/config.example.yaml config/config.yaml
   Edit config/config.yaml and set:
     api.api_key               password clients must send to call this service
     kubernetes.api_server     e.g. https://my-cluster:6443
     kubernetes.bearer_token   token for the cluster
     kubernetes.ca_cert_path   (optional) path to the cluster CA file
     kubernetes.verify_ssl     true/false
   Safer: keep secrets out of the file and use environment variables:
     export KUBE_DEPLOYER_API__API_KEY="your-key"
     export KUBE_DEPLOYER_KUBERNETES__BEARER_TOKEN="your-token"
   (Prefix KUBE_DEPLOYER_, double underscore between levels.)
   To use a different config file: export KUBE_DEPLOYER_CONFIG=/path/file.yaml

3) RUN
     uvicorn app.main:app --host 0.0.0.0 --port 8080
   Host/port in the config file are documentation only; the uvicorn flags
   decide what is actually used.

4) USE
     KEY=your-key
     curl http://localhost:8080/health
     curl -H "Authorization: Bearer $KEY" http://localhost:8080/ready
     curl -X POST -H "Authorization: Bearer $KEY" \
       http://localhost:8080/api/v1/deployments/NAMESPACE/NAME/restart
     curl -X POST -H "Authorization: Bearer $KEY" \
       -H "Content-Type: application/json" -d '{"replicas": 3}' \
       http://localhost:8080/api/v1/deployments/NAMESPACE/NAME/scale

     curl -H "Authorization: Bearer $KEY" \
       http://localhost:8080/api/v1/deployments/NAMESPACE            (list)
     curl -H "Authorization: Bearer $KEY" \
       http://localhost:8080/api/v1/deployments/NAMESPACE/NAME/status (rollout status)

   Restart works like "kubectl rollout restart" (sets the
   kubectl.kubernetes.io/restartedAt annotation). Scale takes the absolute
   replica count wanted (0 or more).

5) TEST (no cluster needed)
     pytest

REUSING IT
  Nothing is hard-coded to a cluster. Point the config or env vars at any
  cluster and token and it works the same way.
