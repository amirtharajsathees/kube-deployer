import os
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

CONFIG_ENV_VAR = "KUBE_DEPLOYER_CONFIG"
DEFAULT_CONFIG_PATH = "config/config.yaml"


def _non_empty(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty")
    return value


class ApiSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    api_key: SecretStr

    @field_validator("host")
    @classmethod
    def _host(cls, v: str) -> str:
        return _non_empty(v)

    @field_validator("api_key")
    @classmethod
    def _api_key(cls, v: SecretStr) -> SecretStr:
        _non_empty(v.get_secret_value())
        return v


class KubernetesSettings(BaseModel):
    api_server: str
    bearer_token: SecretStr
    ca_cert_path: str = ""
    verify_ssl: bool = True
    timeout_seconds: int = Field(default=30, gt=0)

    @field_validator("api_server")
    @classmethod
    def _api_server(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("must be an http:// or https:// URL")
        return v.rstrip("/")

    @field_validator("bearer_token")
    @classmethod
    def _token(cls, v: SecretStr) -> SecretStr:
        _non_empty(v.get_secret_value())
        return v

    @field_validator("ca_cert_path")
    @classmethod
    def _ca(cls, v: str) -> str:
        if v and not os.path.isfile(v):
            raise ValueError("must point to an existing file")
        return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KUBE_DEPLOYER_", env_nested_delimiter="__", extra="ignore"
    )

    api: ApiSettings
    kubernetes: KubernetesSettings


def load_settings(path: str | None = None) -> Settings:
    # yaml file is optional if env vars cover all required fields
    yaml_file = path or os.environ.get(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)

    class FileSettings(Settings):
        @classmethod
        def settings_customise_sources(
            cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
        ):
            # first one wins, so env beats yaml
            return (env_settings, YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file))

    return FileSettings()
