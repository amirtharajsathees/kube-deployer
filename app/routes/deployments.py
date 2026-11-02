from fastapi import APIRouter, Depends, Request

from app.auth import require_api_key
from app.schemas import (
    DeploymentListResponse,
    K8sName,
    RestartResponse,
    RolloutStatusResponse,
    ScaleRequest,
    ScaleResponse,
)
from app.services.deployments import DeploymentService

router = APIRouter(
    prefix="/api/v1/deployments",
    tags=["deployments"],
    dependencies=[Depends(require_api_key)],
)


def get_service(request: Request) -> DeploymentService:
    state = request.app.state
    return DeploymentService(state.apps_api, state.settings.kubernetes.timeout_seconds)


@router.post("/{namespace}/{name}/restart", response_model=RestartResponse)
def restart(namespace: K8sName, name: K8sName, svc: DeploymentService = Depends(get_service)):
    return svc.restart(namespace, name)


@router.post("/{namespace}/{name}/scale", response_model=ScaleResponse)
def scale(
    namespace: K8sName,
    name: K8sName,
    body: ScaleRequest,
    svc: DeploymentService = Depends(get_service),
):
    return svc.scale(namespace, name, body.replicas)


@router.get("/{namespace}", response_model=DeploymentListResponse)
def list_deployments(namespace: K8sName, svc: DeploymentService = Depends(get_service)):
    return svc.list(namespace)


@router.get("/{namespace}/{name}/status", response_model=RolloutStatusResponse)
def rollout_status(namespace: K8sName, name: K8sName, svc: DeploymentService = Depends(get_service)):
    return svc.rollout_status(namespace, name)
