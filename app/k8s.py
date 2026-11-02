from kubernetes import client

from app.config import Settings


def build_api_client(settings: Settings) -> client.ApiClient:
    k = settings.kubernetes
    cfg = client.Configuration()
    cfg.host = k.api_server
    cfg.api_key = {"authorization": f"Bearer {k.bearer_token.get_secret_value()}"}
    cfg.verify_ssl = k.verify_ssl
    if k.ca_cert_path:
        cfg.ssl_ca_cert = k.ca_cert_path
    return client.ApiClient(configuration=cfg)


def build_apps_api(api_client: client.ApiClient) -> client.AppsV1Api:
    return client.AppsV1Api(api_client)


def build_version_api(api_client: client.ApiClient) -> client.VersionApi:
    return client.VersionApi(api_client)
