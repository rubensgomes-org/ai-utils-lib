"""Pydantic models for the config.yaml sections."""

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from ai_utils_lib.constants import (
    DEFAULT_MAX_CONCURRENT_PROMPTS,
    DEFAULT_MODEL_TIMEOUT_SECONDS,
    DEFAULT_OAUTH_CALLBACK_PORT,
    DEFAULT_WEBAPP_PORT,
)

__all__ = ["Azure", "Foundry", "MCP", "Model", "Web", "AppConfig"]


class _FrozenModel(BaseModel):
    """Immutable base, as loaded configs are cached and shared."""

    model_config = ConfigDict(frozen=True)


class Azure(_FrozenModel):
    """The ``azure`` section of config.yaml."""

    app_config_prefix: str
    app_config_separator: str = Field(default="/", min_length=1)
    secret_prefix: str
    secret_separator: str = Field(default="--", min_length=1)


class Foundry(_FrozenModel):
    """The ``foundry`` section of config.yaml."""

    project_endpoint: HttpUrl


class MCP(_FrozenModel):
    """A named MCP server entry in the ``mcp`` section of config.yaml."""

    url: HttpUrl
    is_oauth: bool = False
    token_dir: str = "~/.oauth_tokens"
    callback_port: int = Field(default=DEFAULT_OAUTH_CALLBACK_PORT, gt=0)


class Model(_FrozenModel):
    """The ``model`` section of config.yaml."""

    api_style: Literal["chat", "responses"] = "responses"
    base_url: HttpUrl
    name: str = Field(min_length=1)
    # `api_key_env` may be None if we are using Azure Entra ID credential
    api_key_env: str | None = None
    instructions: str
    is_stateful: bool = False
    max_concurrent_prompts: int = Field(
        default=DEFAULT_MAX_CONCURRENT_PROMPTS, gt=0
    )
    timeout_seconds: int = Field(default=DEFAULT_MODEL_TIMEOUT_SECONDS, gt=0)
    temperature: float | None = Field(default=None, ge=0, le=2)
    # When not given, set from the environment variable named by
    # `api_key_env`, or from Key Vault by the Azure loader; None when
    # unresolved.
    api_key: str | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="before")
    @classmethod
    def _read_api_key(cls, data: Any) -> Any:
        """Sets an unset ``api_key`` from the variable named by
        ``api_key_env``."""
        # Model keeps an api_key you pass in, and only reads the environment
        # variable named by api_key_env when no key was given.
        if not isinstance(data, dict) or data.get("api_key"):
            # leave the input data alone if data already has api_key
            return data
        api_key_env = data.get("api_key_env")
        if not api_key_env or not isinstance(api_key_env, str):
            # leave the input data alone if data already has no api_key_env
            return data
        return {**data, "api_key": os.environ.get(api_key_env) or None}


class Web(_FrozenModel):
    """The ``web`` section of config.yaml."""

    host: str = "localhost"
    port: int = Field(default=DEFAULT_WEBAPP_PORT, gt=0)


class AppConfig(_FrozenModel):
    """The full config.yaml."""

    azure: Azure
    foundry: Foundry
    mcp: dict[str, MCP] = Field(default_factory=dict)
    model: Model
    web: Web = Field(default_factory=Web)
    logging: dict[str, Any]
