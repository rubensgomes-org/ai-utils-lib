"""Generic configuration loader for AI Utilities."""

import logging
import os
from pathlib import Path

from ai_utils_lib.azure.azure_load_config import (
    aload_config as _aload_azure_config,
)
from ai_utils_lib.config_models import AppConfig
from ai_utils_lib.file.file_load_config import load_config as _load_file_config

__all__ = ["aload_config"]

logger = logging.getLogger(__name__)


async def aload_config(config: Path) -> AppConfig:
    """Load the ``config.yaml`` at ``config`` for the current runtime.

    When ``APP_CONFIG_ENDPOINT`` is set, the YAML is overlaid with App
    Configuration settings labeled ``APP_ENV``; those are not cached.

    Raises:
        RuntimeError: ``APP_CONFIG_ENDPOINT`` is set but ``APP_ENV`` is not.
    """
    app_config: AppConfig = _load_file_config(config)
    app_configuration = _app_configuration_source()
    if app_configuration is None:
        return app_config
    return await _aload_azure_config(app_config, *app_configuration)


def _app_configuration_source() -> tuple[str, str] | None:
    """Return the App Configuration endpoint and label, if configured."""
    # APP_CONFIG_ENDPOINT and APP_ENV are environment variables set in every
    # ACA by Rubens' Terraform azure-iac project.
    appcs_endpoint: str | None = os.environ.get("APP_CONFIG_ENDPOINT")
    if not appcs_endpoint:
        return None
    label: str | None = os.environ.get("APP_ENV")
    if not label:
        error_msg: str = (
            "APP_ENV must be set when APP_CONFIG_ENDPOINT is set, to select "
            "the App Configuration label."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return appcs_endpoint, label
