from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import require_api_key
from app.schemas import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse, dependencies=[Depends(require_api_key)])
def ready(request: Request) -> ReadyResponse:
    timeout = request.app.state.settings.kubernetes.timeout_seconds
    try:
        request.app.state.version_api.get_code(_request_timeout=timeout)
    except Exception:
        raise HTTPException(status_code=503, detail="Kubernetes API unreachable") from None
    return ReadyResponse()
