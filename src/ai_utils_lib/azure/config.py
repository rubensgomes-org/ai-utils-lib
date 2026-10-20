"""Azure App Configuration based loader for AI Utilities."""

import asyncio
import functools
import logging
import os
from importlib.resources.abc import Traversable
from typing import Any

from azure.appconfiguration import ConfigurationSetting
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.app_configuration import list_settings
from ai_utils_lib.azure.key_vault import read_secret
from ai_utils_lib.config.file.config import read_yaml, resolve_config_path
from ai_utils_lib.config.models import AppConfig, Azure

__all__ = ["load_config"]

logger = logging.getLogger(__name__)


@functools.cache
def load_config(
    package: str, appcs_endpoint: str, label_filter: str
) -> AppConfig:
    """Load ``config.yaml`` from ``package`` overlaid with App Configuration.

    Settings under ``azure.app_config_prefix`` and labeled ``label_filter``
    are read from the store at ``appcs_endpoint`` and override the
    matching YAML values. ``model.api_key`` is read from Key Vault unless
    the variable named by ``model.api_key_env`` holds it.

    Must not be called from a running event loop.

    Raises:
        KeyError: Key Vault is needed but ``KEY_VAULT_URI`` is not set.
        ValueError: ``label_filter`` contains ``*`` or ``,``, or the Key
            Vault secret name is invalid, or its value is empty or blank.
        HttpResponseError: An App Configuration or Key Vault request
            failed, including ``ResourceNotFoundError`` and
            ``ClientAuthenticationError``.
    """
    logger.debug(
        "Loading Azure App Configuration with package: %s, "
        "appcs_endpoint: %s, label_filter: %s",
        package,
        appcs_endpoint,
        label_filter,
    )
    config_yaml_file: Traversable = resolve_config_path(package)
    config_dict: dict[str, Any] = read_yaml(config_yaml_file)
    return asyncio.run(_load_config(config_dict, appcs_endpoint, label_filter))


async def _load_config(
    config_dict: dict[str, Any], appcs_endpoint: str, label_filter: str
) -> AppConfig:
    """Return ``config_dict`` overlaid with settings, with the API key."""
    # DefaultAzureCredential tries, in order:
    #   1. Environment variables (e.g., AZURE_CLIENT_ID, AZURE_TENANT_ID)
    #   2. Managed identity (e.g., the UAMI of an Azure Container App)
    #   3. Your Azure CLI login
    async with DefaultAzureCredential() as credential:
        return await _load_config_with_credential(
            credential, config_dict, appcs_endpoint, label_filter
        )


async def _load_config_with_credential(
    credential: AsyncTokenCredential,
    config_dict: dict[str, Any],
    appcs_endpoint: str,
    label_filter: str,
) -> AppConfig:
    """Return ``config_dict`` overlaid with settings, with the API key."""
    azure = Azure.model_validate(config_dict.get("azure"))
    logger.debug(
        "prefix: %s, separator: %s",
        azure.app_config_prefix,
        azure.app_config_separator,
    )
    settings_dict: dict[str, Any] = await _convert_to_dict(
        credential,
        appcs_endpoint,
        azure.app_config_separator,
        azure.app_config_prefix,
        label_filter,
    )
    config = AppConfig.model_validate(_deep_merge(config_dict, settings_dict))
    return await _with_api_key(credential, config)


async def _with_api_key(
    credential: AsyncTokenCredential, config: AppConfig
) -> AppConfig:
    """Return ``config`` with ``model.api_key`` set, read from Key Vault
    when the variable named by ``model.api_key_env`` did not provide it.
    """
    api_key_env: str | None = config.model.api_key_env
    if not api_key_env or config.model.api_key:
        return config
    secret_name: str = _secret_name(config.azure, api_key_env)
    # KEY_VAULT_URI is an environment variable set in every ACA by
    # Rubens' Terraform azure-iac project.
    vault_url: str | None = os.environ.get("KEY_VAULT_URI")
    if not vault_url:
        raise KeyError(
            f"KEY_VAULT_URI must be set to read Key Vault secret "
            f"{secret_name}, as {api_key_env} is not set"
        )
    api_key: str = await read_secret(credential, vault_url, secret_name)
    model = config.model.model_copy(update={"api_key": api_key})
    return config.model_copy(update={"model": model})


def _secret_name(azure: Azure, api_key_env: str) -> str:
    """Return the Key Vault secret name for ``api_key_env``.

    Underscores become dashes, as Key Vault secret names disallow them.
    """
    secret_key: str = api_key_env.replace("_", "-")
    return f"{azure.secret_prefix}{azure.secret_separator}{secret_key}"


async def _convert_to_dict(
    credential: AsyncTokenCredential,
    appcs_endpoint: str,
    separator: str,
    prefix: str,
    label_filter: str,
) -> dict[str, Any]:
    """Return the settings under ``prefix`` as a nested dictionary.

    ``prefix`` is completed with a trailing ``separator`` if missing, then
    removed, and the remaining key is split on ``separator``, e.g.
    ``prefix/model/name = x`` becomes ``{"model": {"name": "x"}}``.
    """
    if not prefix.endswith(separator):
        prefix = f"{prefix}{separator}"
    key_filter: str = f"{prefix}*"
    settings: list[ConfigurationSetting] = await list_settings(
        credential, appcs_endpoint, key_filter, label_filter
    )
    logger.debug(
        "Read %d App Configuration settings with key_filter: %s",
        len(settings),
        key_filter,
    )
    response: dict[str, Any] = {}
    for setting in settings:
        key_path: str = setting.key.removeprefix(prefix)
        _set_nested(response, key_path.split(separator), setting.value)
    return response


def _set_nested(target: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set ``value`` in ``target`` at the nested path given by ``keys``."""
    if not all(keys):
        raise ValueError(f"Setting path {keys} has an empty segment")
    *parents, leaf = keys
    node: dict[str, Any] = target
    for key in parents:
        child = node.setdefault(key, {})
        if not isinstance(child, dict):
            raise ValueError(
                f"Setting path {keys} conflicts with existing value at "
                f"'{key}'"
            )
        node = child
    if isinstance(node.get(leaf), dict):
        raise ValueError(f"Setting path {keys} conflicts with a section")
    node[leaf] = value


def _deep_merge(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Return ``base`` recursively updated with ``override`` values."""
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(base_value, value)
        else:
            merged[key] = value
    return merged
