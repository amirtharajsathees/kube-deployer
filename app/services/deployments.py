from datetime import datetime, timezone

from app.errors import to_http_error

RESTARTED_AT = "kubectl.kubernetes.io/restartedAt"
STRATEGIC_MERGE = "application/strategic-merge-patch+json"


class DeploymentService:
    def __init__(self, apps_api, timeout_seconds: int):
        self._api = apps_api
        self._timeout = timeout_seconds

    def _read(self, namespace: str, name: str):
        return self._api.read_namespaced_deployment(
            name, namespace, _request_timeout=self._timeout
        )

    def _patch(self, namespace: str, name: str, body: dict) -> None:
        self._api.patch_namespaced_deployment(
            name,
            namespace,
            body,
            _content_type=STRATEGIC_MERGE,
            _request_timeout=self._timeout,
        )

    def restart(self, namespace: str, name: str) -> dict:
        restarted_at = datetime.now(timezone.utc).isoformat()
        body = {"spec": {"template": {"metadata": {"annotations": {RESTARTED_AT: restarted_at}}}}}
        try:
            self._read(namespace, name)
            self._patch(namespace, name, body)
        except Exception as exc:
            raise to_http_error(exc) from None
        return {"namespace": namespace, "name": name, "restarted_at": restarted_at}

    def scale(self, namespace: str, name: str, replicas: int) -> dict:
        try:
            deployment = self._read(namespace, name)
            spec = getattr(deployment, "spec", None)
            previous = getattr(spec, "replicas", None)
            self._patch(namespace, name, {"spec": {"replicas": replicas}})
        except Exception as exc:
            raise to_http_error(exc) from None
        return {
            "namespace": namespace,
            "name": name,
            "previous_replicas": 0 if previous is None else previous,
            "replicas": replicas,
        }

    def list(self, namespace: str) -> dict:
        try:
            result = self._api.list_namespaced_deployment(
                namespace, _request_timeout=self._timeout
            )
        except Exception as exc:
            raise to_http_error(exc) from None
        items = [
            {
                "name": d.metadata.name,
                "namespace": namespace,
                "replicas": _count(d.spec, "replicas"),
                "ready_replicas": _count(d.status, "ready_replicas"),
            }
            for d in result.items
        ]
        return {"namespace": namespace, "items": items}

    def rollout_status(self, namespace: str, name: str) -> dict:
        # same checks kubectl rollout status does
        try:
            d = self._read(namespace, name)
        except Exception as exc:
            raise to_http_error(exc) from None
        desired = _count(d.spec, "replicas")
        updated = _count(d.status, "updated_replicas")
        total = _count(d.status, "replicas")
        available = _count(d.status, "available_replicas")
        generation = _count(d.metadata, "generation")
        observed = _count(d.status, "observed_generation")

        if generation > observed:
            message = "Waiting for deployment spec update to be observed"
        elif updated < desired:
            message = f"{updated} of {desired} replicas updated"
        elif total > updated:
            message = f"{total - updated} old replicas pending termination"
        elif available < updated:
            message = f"{available} of {updated} updated replicas available"
        else:
            message = "Rollout complete"
        return {
            "namespace": namespace,
            "name": name,
            "rolled_out": message == "Rollout complete",
            "message": message,
            "desired_replicas": desired,
            "updated_replicas": updated,
            "ready_replicas": _count(d.status, "ready_replicas"),
            "available_replicas": available,
        }


def _count(obj, attr: str) -> int:
    # k8s leaves out fields that are 0
    return getattr(obj, attr, None) or 0
