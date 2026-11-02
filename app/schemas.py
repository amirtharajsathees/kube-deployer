from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, StrictInt

# k8s names: dns label, 63 chars max
K8sName = Annotated[str, Path(pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63)]


class ScaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replicas: StrictInt = Field(ge=0)


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str = "ready"


class RestartResponse(BaseModel):
    namespace: str
    name: str
    restarted_at: str


class ScaleResponse(BaseModel):
    namespace: str
    name: str
    previous_replicas: int
    replicas: int


class DeploymentSummary(BaseModel):
    name: str
    namespace: str
    replicas: int
    ready_replicas: int


class DeploymentListResponse(BaseModel):
    namespace: str
    items: list[DeploymentSummary]


class RolloutStatusResponse(BaseModel):
    namespace: str
    name: str
    rolled_out: bool
    message: str
    desired_replicas: int
    updated_replicas: int
    ready_replicas: int
    available_replicas: int
