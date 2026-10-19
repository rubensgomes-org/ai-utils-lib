"""Azure App Configuration based loader for AI Utilities."""

import asyncio
import functools
import logging
from importlib.resources.abc import Traversable
from typing import Any

from azure.appconfiguration import ConfigurationSetting

from ai_utils_lib.config.azure.app_configuration import list_settings
from ai_utils_lib.config.file.config import read_yaml, resolve_config_path
from ai_utils_lib.config.models import AppConfig

__all__ = ["load_config"]

logger = logging.getLogger(__name__)


@functools.cache
def load_config(
    package: str, appcs_endpoint: str, label_filter: str
) -> AppConfig:
    """Load ``config.yaml`` from ``package`` overlaid with App Configuration.

    Settings under ``azure.app_config_prefix`` and labeled ``label_filter``
    are read from the store at ``appcs_endpoint`` and override the
    matching YAML values.

    Must not be called from a running event loop.
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
    prefix: str = config_dict["azure"]["app_config_prefix"]
    separator: str = config_dict["azure"]["app_config_separator"]
    logger.debug("prefix: %s, separator: %s", prefix, separator)
    settings_dict: dict[str, Any] = asyncio.run(
        _convert_to_dict(appcs_endpoint, separator, prefix, label_filter)
    )
    combined_config_dict: dict[str, Any] = _deep_merge(
        config_dict, settings_dict
    )
    return AppConfig.model_validate(combined_config_dict)


async def _convert_to_dict(
    appcs_endpoint: str, separator: str, prefix: str, label_filter: str
) -> dict[str, Any]:
    """Return the settings under ``prefix`` as a nested dictionary.

    The prefix is removed and the remaining key is split on ``/``, e.g.
    ``prefix/model/name = x`` becomes ``{"model": {"name": "x"}}``.
    """
    key_filter: str = f"{prefix}*"
    settings: list[ConfigurationSetting] = await list_settings(
        appcs_endpoint, key_filter, label_filter
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


if __name__ == "__main__":
    # TESTING ONLY!!!
    _APP_CONFIG_ENDPOINT = "https://appcs-rgomes-lab.azconfig.io"
    config: AppConfig = load_config(
        "ai_utils_lib.config", _APP_CONFIG_ENDPOINT, "lab"
    )
    print(f"AppConfig = {config}")
