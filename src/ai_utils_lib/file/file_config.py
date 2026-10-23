"""File-based configuration loader for AI Utilities."""

import functools
import logging.config
from pathlib import Path
from typing import Any

import yaml

from ai_utils_lib.config_models import AppConfig

__all__ = ["load_config", "configure_logging"]


@functools.cache
def load_config(config: Path) -> AppConfig:
    """Load and validate the ``config.yaml`` file at ``config``.

    Raises:
        FileNotFoundError: ``config`` does not exist.
        ValueError: The YAML is invalid or is not a mapping.
        ValidationError: The configuration is invalid.
    """
    config_dict: dict[str, Any] = _read_yaml(config)
    return AppConfig.model_validate(config_dict)


def configure_logging(config: AppConfig) -> None:
    """Apply the ``logging`` section of ``config`` via ``dictConfig``."""
    logging.config.dictConfig(config.logging)


def _read_yaml(path: Path) -> dict[str, Any]:
    """Return the YAML mapping in the file at ``path``."""
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {path}") from error
    if not isinstance(content, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return content
