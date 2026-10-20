"""Azure App Configuration based loader for AI Utilities."""

import asyncio
import functools
import logging
import os
import re
from importlib.resources.abc import Traversable
from typing import Any, NoReturn

from azure.appconfiguration import ConfigurationSetting
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.app_configuration import list_settings
from ai_utils_lib.azure.key_vault import read_secret
from ai_utils_lib.config.file_load_config import read_yaml, resolve_config_path
from ai_utils_lib.config.models import AppConfig, Azure

__all__ = ["aload_config", "load_config"]

logger = logging.getLogger(__name__)

# Characters App Configuration key filters treat as wildcard or separator.
KEY_FILTER_SPECIAL_CHARS = re.compile(r"[*,\\]")

# ``azure`` keys that select the settings read, so only config.yaml sets them.
STORE_LOOKUP_KEYS = ("app_config_prefix", "app_config_separator")


@functools.cache
def load_config(
    package: str, appcs_endpoint: str, label_filter: str
) -> AppConfig:
    """Return the cached result of ``aload_config`` for synchronous code.

    Also raises the errors of ``aload_config``.

    Raises:
        RuntimeError: Called from a running event loop; await
            ``aload_config`` instead.
    """
    _reject_running_loop()
    return asyncio.run(aload_config(package, appcs_endpoint, label_filter))


async def aload_config(
    package: str, appcs_endpoint: str, label_filter: str
) -> AppConfig:
    """Load ``config.yaml`` from ``package`` overlaid with App Configuration.

    Settings under ``azure.app_config_prefix`` and labeled ``label_filter``
    are read from the store at ``appcs_endpoint`` and override the
    matching YAML values. ``model.api_key`` is read from Key Vault unless
    the variable named by ``model.api_key_env`` holds it. Not cached.

    Raises:
        RuntimeError: Key Vault is needed but ``KEY_VAULT_URI`` is not set.
        ValueError: The YAML is invalid, ``label_filter`` contains ``*``
            or ``,``, a setting has no value, or its key has an empty
            segment or conflicts with another, or the Key Vault secret
            name or value is invalid.
        ValidationError: The merged configuration is invalid.
        HttpResponseError: An App Configuration or Key Vault request
            failed, including ``ResourceNotFoundError`` and
            ``ClientAuthenticationError``.
        ServiceRequestError: App Configuration or Key Vault is unreachable.
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
    async with DefaultAzureCredential() as credential:
        return await _load_config_with_credential(
            credential, config_dict, appcs_endpoint, label_filter
        )


def _reject_running_loop() -> None:
    """Raise ``RuntimeError`` if an event loop runs in this thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    error_msg: str = (
        "load_config cannot run in an event loop; await aload_config."
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


async def _load_config_with_credential(
    credential: AsyncTokenCredential,
    config_dict: dict[str, Any],
    appcs_endpoint: str,
    label_filter: str,
) -> AppConfig:
    """Return ``config_dict`` overlaid with settings, with the API key."""
    azure = Azure.model_validate(config_dict.get("azure"))
    logger.debug(
        "App Configuration prefix: %s, separator: %s",
        azure.app_config_prefix,
        azure.app_config_separator,
    )
    settings_tree: dict[str, Any] = await _read_settings_tree(
        credential,
        appcs_endpoint,
        azure.app_config_separator,
        azure.app_config_prefix,
        label_filter,
    )
    settings_tree = _without_store_lookup_settings(settings_tree, azure)
    config = AppConfig.model_validate(_deep_merge(config_dict, settings_tree))
    return await _with_api_key(credential, config)


async def _with_api_key(
    credential: AsyncTokenCredential, config: AppConfig
) -> AppConfig:
    """Return ``config`` with ``model.api_key`` set, if needed from Key Vault.

    Key Vault is read only when the variable named by
    ``model.api_key_env`` did not provide the key.
    """
    api_key_env: str | None = config.model.api_key_env
    if not api_key_env or config.model.api_key:
        return config
    secret_name: str = _secret_name(config.azure, api_key_env)
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
    model = config.model.model_copy(update={"api_key": api_key})
    return config.model_copy(update={"model": model})


def _secret_name(azure: Azure, api_key_env: str) -> str:
    """Return the Key Vault secret name for ``api_key_env``.

    Underscores become dashes, as Key Vault secret names disallow them.
    """
    secret_key: str = api_key_env.replace("_", "-")
    return f"{azure.secret_prefix}{azure.secret_separator}{secret_key}"


async def _read_settings_tree(
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


def _without_store_lookup_settings(
    settings_tree: dict[str, Any], azure: Azure
) -> dict[str, Any]:
    """Return ``settings_tree`` without ``STORE_LOOKUP_KEYS``.

    A warning is logged for each value that differs from ``azure``.
    """
    azure_settings = settings_tree.get("azure")
    if not isinstance(azure_settings, dict):
        return settings_tree
    for key in STORE_LOOKUP_KEYS:
        yaml_value = getattr(azure, key)
        if key in azure_settings and azure_settings[key] != yaml_value:
            logger.warning(
                "Ignoring App Configuration azure.%s %r; config.yaml sets %r.",
                key,
                azure_settings[key],
                yaml_value,
            )
    other_settings = {
        key: value
        for key, value in azure_settings.items()
        if key not in STORE_LOOKUP_KEYS
    }
    return {**settings_tree, "azure": other_settings}


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
