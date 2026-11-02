from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import load_settings
from app.k8s import build_api_client, build_apps_api, build_version_api
from app.routes import deployments, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    api_client = build_api_client(settings)
    app.state.settings = settings
    app.state.api_client = api_client
    app.state.apps_api = build_apps_api(api_client)
    app.state.version_api = build_version_api(api_client)
    try:
        yield
    finally:
        api_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="kube-deployer", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(deployments.router)
    return app


app = create_app()
