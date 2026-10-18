"""File-based configuration loader for AI Utilities."""

import functools
import logging.config
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

import yaml

from ai_utils_lib.config.models import AppConfig
from ai_utils_lib.constants import CONFIG_FILE_NAME

__all__ = ["load_config", "configure_logging"]


@functools.cache
def load_config(package: str) -> AppConfig:
    """Load and validate ``config.yaml`` from the root of ``package``.

    Applications typically pass their root package name, e.g.
    ``load_config(__package__)`` or ``load_config("my_app")``.
    """
    config_yaml_file: Traversable = _resolve_config_path(package)
    config_dict: dict[str, Any] = _read_yaml(config_yaml_file)
    return AppConfig.model_validate(config_dict)


def configure_logging(config: AppConfig) -> None:
    """Apply the ``logging`` section of ``config`` via ``dictConfig``."""
    logging.config.dictConfig(config.logging)


def _read_yaml(resource: Traversable) -> dict[str, Any]:
    """Return the YAML mapping in ``resource``."""
    try:
        content = yaml.safe_load(resource.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {resource}") from error
    if not isinstance(content, dict):
        raise ValueError(f"Expected a YAML mapping in {resource}")
    return content


def _resolve_config_path(package: str) -> Traversable:
    """Return ``config.yaml`` located at the root ``package``."""
    return files(package).joinpath(CONFIG_FILE_NAME)
