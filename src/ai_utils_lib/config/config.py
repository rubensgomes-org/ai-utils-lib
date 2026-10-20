"""Generic configuration loader for AI Utilities."""

import os

from ai_utils_lib.azure.config import load_config as _load_azure_config
from ai_utils_lib.config.file.config import load_config as _load_file_config
from ai_utils_lib.config.models import AppConfig

__all__ = ["load_config"]


def load_config(package: str) -> AppConfig:
    """Load the ``config.yaml`` of ``package`` for the current runtime.

    When ``APP_CONFIG_ENDPOINT`` is set, the YAML is overlaid with Azure App
    Configuration settings labeled ``APP_ENV``; otherwise only the YAML is
    loaded.

    Raises:
        KeyError: ``APP_CONFIG_ENDPOINT`` is set but ``APP_ENV`` is not.
    """
    # APP_CONFIG_ENDPOINT is an environment variable set in every ACA by
    # Rubens' Terraform azure-iac project.
    aca_endpoint: str | None = os.environ.get("APP_CONFIG_ENDPOINT")

    if aca_endpoint:
        # application is running in Azure Container Apps
        # APP_ENV is an environment variable set in every ACA by
        # Rubens' Terraform azure-iac project.
        label: str = os.environ["APP_ENV"]  # KeyError if not defined
        return _load_azure_config(package, aca_endpoint, label)

    # application is running locally
    return _load_file_config(package)


if __name__ == "__main__":
    # TESTING ONLY!!!
    _PACKAGE = "ai_utils_lib.config"
    # load configuration settings from Azure App Configuration
    os.environ["APP_CONFIG_ENDPOINT"] = "https://appcs-rgomes-lab.azconfig.io"
    os.environ["APP_ENV"] = "lab"
    config: AppConfig = load_config(_PACKAGE)
    print(f"Azure AppConfig = {config}")

    # load configuration settings from local config.yaml
    os.environ.pop("APP_CONFIG_ENDPOINT", None)
    config = load_config(_PACKAGE)
    print(f"Local AppConfig = {config}")
