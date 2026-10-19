"""Pydantic models for the config.yaml sections."""

import os
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from ai_utils_lib.constants import (
    DEFAULT_MAX_CONCURRENT_PROMPTS,
    DEFAULT_MODEL_TIMEOUT_SECONDS,
    DEFAULT_OAUTH_CALLBACK_PORT,
    DEFAULT_WEBAPP_PORT,
)

__all__ = ["Azure", "Foundry", "MCP", "Model", "Web", "AppConfig"]


class Azure(BaseModel):
    """The ``azure`` section of config.yaml."""

    app_config_prefix: str
    app_config_separator: str = "/"
    secret_prefix: str


class Foundry(BaseModel):
    """The ``foundry`` section of config.yaml."""

    project_endpoint: HttpUrl


class MCP(BaseModel):
    """A named MCP server entry in the ``mcp`` section of config.yaml."""

    url: HttpUrl
    is_oauth: bool = False
    token_dir: str = "~/.oauth_tokens"
    callback_port: int = Field(default=DEFAULT_OAUTH_CALLBACK_PORT, gt=0)


class Model(BaseModel):
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
    # Set from the environment variable named by `api_key_env`; None when
    # either is unset or empty.
    api_key: str | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def _read_api_key(self) -> Self:
        """Sets ``api_key`` from the variable named by ``api_key_env``."""
        if self.api_key_env:
            self.api_key = os.environ.get(self.api_key_env) or None
        else:
            self.api_key = None
        return self


class Web(BaseModel):
    """The ``web`` section of config.yaml."""

    host: str = "localhost"
    port: int = Field(default=DEFAULT_WEBAPP_PORT, gt=0)


class AppConfig(BaseModel):
    """The full config.yaml."""

    azure: Azure
    foundry: Foundry
    mcp: dict[str, MCP]
    model: Model
    web: Web
    logging: dict[str, Any]
