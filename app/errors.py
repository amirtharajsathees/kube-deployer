import logging

from fastapi import HTTPException
from kubernetes.client.exceptions import ApiException

log = logging.getLogger("kube-deployer")


def to_http_error(exc: Exception) -> HTTPException:
    # only log the exception type, the message/body can have secrets in it
    if isinstance(exc, ApiException) and exc.status == 404:
        return HTTPException(status_code=404, detail="Deployment not found")
    log.warning("Kubernetes request failed: %s", type(exc).__name__)
    return HTTPException(status_code=502, detail="Kubernetes API request failed")
