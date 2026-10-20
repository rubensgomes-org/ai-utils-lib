"""Generic configuration loader for AI Utilities."""

import logging
import os

from ai_utils_lib.config.azure_load_config import (
    aload_config as _aload_azure_config,
)
from ai_utils_lib.config.azure_load_config import (
    load_config as _load_azure_config,
)
from ai_utils_lib.config.file_load_config import (
    load_config as _load_file_config,
)
from ai_utils_lib.config.models import AppConfig

__all__ = ["aload_config", "load_config"]

logger = logging.getLogger(__name__)


def load_config(package: str) -> AppConfig:
    """Load the ``config.yaml`` of ``package`` for the current runtime.

    When ``APP_CONFIG_ENDPOINT`` is set, the YAML is overlaid with Azure App
    Configuration settings labeled ``APP_ENV``; otherwise only the YAML is
    loaded. Async code must await ``aload_config`` instead.

    Also raises the errors of the Azure and file loaders.

    Raises:
        RuntimeError: ``APP_CONFIG_ENDPOINT`` is set but ``APP_ENV`` is not
            set or is empty.
    """
    app_configuration = _app_configuration_source()
    if app_configuration is None:
        return _load_file_config(package)
    return _load_azure_config(package, *app_configuration)


async def aload_config(package: str) -> AppConfig:
    """Async ``load_config``; App Configuration results are not cached."""
    app_configuration = _app_configuration_source()
    if app_configuration is None:
        return _load_file_config(package)
    return await _aload_azure_config(package, *app_configuration)


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
