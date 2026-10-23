"""Azure App Configuration based loader for AI Utilities."""

import logging
import os
import re
from typing import Any, NoReturn

from azure.appconfiguration import ConfigurationSetting
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.app_configuration import list_settings
from ai_utils_lib.azure.key_vault import read_secret
from ai_utils_lib.config_models import AppConfig, Azure

__all__ = ["aload_config"]

logger = logging.getLogger(__name__)

# Characters App Configuration key filters treat as wildcard or separator.
KEY_FILTER_SPECIAL_CHARS = re.compile(r"[*,\\]")


async def aload_config(
    app_config: AppConfig, appcs_endpoint: str, label_filter: str
) -> AppConfig:
    """Return ``app_config`` overlaid with App Configuration settings.

    ``model.api_key`` is read from Key Vault unless the variable named by
    ``model.api_key_env`` holds it.

    Raises:
        RuntimeError: Key Vault is needed but ``KEY_VAULT_URI`` is not set.
        ValueError: ``label_filter`` contains ``*`` or ``,``, a setting has
            no value, or its key has an empty segment or conflicts with
            another, or the Key Vault secret name or value is invalid.
        ValidationError: The merged configuration is invalid.
        HttpResponseError: An App Configuration or Key Vault request
            failed, including ``ResourceNotFoundError`` and
            ``ClientAuthenticationError``.
        ServiceRequestError: App Configuration or Key Vault is unreachable.
    """
    logger.debug(
        "Loading Azure App Configuration with AppConfig: %s, "
        "appcs_endpoint: %s, label_filter: %s",
        app_config,
        appcs_endpoint,
        label_filter,
    )
    async with DefaultAzureCredential() as credential:
        settings: dict[str, Any] = await _load_settings(
            credential,
            appcs_endpoint,
            app_config.azure.app_config_separator,
            app_config.azure.app_config_prefix,
            label_filter,
        )
        merged_dict: dict[str, Any] = _deep_merge(
            app_config.model_dump(), settings
        )
        merged_app_config: AppConfig = AppConfig.model_validate(merged_dict)
        return await _with_api_key(credential, merged_app_config)


async def _with_api_key(
    credential: AsyncTokenCredential, app_config: AppConfig
) -> AppConfig:
    """Return ``app_config`` with ``model.api_key`` from Key Vault if needed.

    Key Vault is read only when the variable named by
    ``model.api_key_env`` did not provide the key.
    """
    api_key_env: str | None = app_config.model.api_key_env
    if not api_key_env or app_config.model.api_key:
        return app_config
    secret_name: str = _secret_name(app_config.azure, api_key_env)
    # KEY_VAULT_URI is an environment variable set in every ACA by
    # Rubens' Terraform azure-iac project.
    vault_url: str | None = os.environ.get("KEY_VAULT_URI")
    if not vault_url:
        error_msg: str = (
            f"KEY_VAULT_URI must be set to read Key Vault secret "
            f"{secret_name}, as {api_key_env} is not set."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    api_key: str = await read_secret(credential, vault_url, secret_name)
    model = app_config.model.model_copy(update={"api_key": api_key})
    return app_config.model_copy(update={"model": model})


def _secret_name(azure: Azure, api_key_env: str) -> str:
    """Return the Key Vault secret name for ``api_key_env``.

    Underscores become dashes, as Key Vault secret names disallow them.
    """
    secret_key: str = api_key_env.replace("_", "-")
    return f"{azure.secret_prefix}{azure.secret_separator}{secret_key}"


async def _load_settings(
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
    key_filter: str = f"{_escape_key_filter(prefix)}*"
    settings: list[ConfigurationSetting] = await list_settings(
        credential, appcs_endpoint, key_filter, label_filter
    )
    logger.debug(
        "Read %d App Configuration settings with key_filter: %s",
        len(settings),
        key_filter,
    )
    settings_tree: dict[str, Any] = {}
    for setting in settings:
        if setting.value is None:
            _raise_value_error(
                f"App Configuration setting {setting.key} has no value."
            )
        key_path: str = setting.key.removeprefix(prefix)
        _set_nested(settings_tree, key_path.split(separator), setting.value)
    return settings_tree


def _escape_key_filter(key: str) -> str:
    """Return ``key`` with key filter special characters escaped."""
    return KEY_FILTER_SPECIAL_CHARS.sub(r"\\\g<0>", key)


def _set_nested(target: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set ``value`` in ``target`` at the nested path given by ``keys``."""
    if not all(keys):
        _raise_value_error(f"Setting path {keys} has an empty segment.")
    *parents, leaf = keys
    node: dict[str, Any] = target
    for key in parents:
        child = node.setdefault(key, {})
        if not isinstance(child, dict):
            _raise_value_error(
                f"Setting path {keys} conflicts with existing value at "
                f"'{key}'."
            )
        node = child
    if isinstance(node.get(leaf), dict):
        _raise_value_error(f"Setting path {keys} conflicts with a section.")
    node[leaf] = value


def _raise_value_error(error_msg: str) -> NoReturn:
    """Log ``error_msg`` and raise it as a ``ValueError``."""
    logger.error(error_msg)
    raise ValueError(error_msg)


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
