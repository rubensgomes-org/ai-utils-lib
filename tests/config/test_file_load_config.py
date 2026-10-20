"""Tests for ai_utils_lib.config.file_load_config."""

import copy
import logging
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ai_utils_lib.config.file_load_config import configure_logging, load_config
from ai_utils_lib.config.models import AppConfig, Web
from ai_utils_lib.constants import CONFIG_FILE_NAME

BUNDLED_CONFIG_PACKAGE = "ai_utils_lib.config"
PROBE_LOGGER_NAME = "tests.config.file_load_config.probe"

PackageFactory = Callable[[str | None], str]


@pytest.fixture(autouse=True)
def clear_config_cache() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


@pytest.fixture
def make_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageFactory:
    """Create an importable package, optionally holding ``config.yaml``."""
    monkeypatch.syspath_prepend(tmp_path)

    def factory(config_text: str | None) -> str:
        name = f"pkg_{uuid.uuid4().hex}"
        package_dir = tmp_path / name
        package_dir.mkdir()
        (package_dir / "__init__.py").touch()
        if config_text is not None:
            (package_dir / CONFIG_FILE_NAME).write_text(
                config_text, encoding="utf-8"
            )
        return name

    return factory


@pytest.fixture
def valid_config() -> dict[str, Any]:
    return {
        "azure": {
            "app_config_prefix": "test-prefix/",
            "secret_prefix": "test-prefix",
            "secret_separator": "--",
        },
        "foundry": {"project_endpoint": "https://example.com/foundry"},
        "mcp": {"calc": {"url": "https://example.com/mcp", "token_dir": "~"}},
        "model": {
            "base_url": "https://example.com/v1",
            "name": "test-model",
            "instructions": "Be helpful.",
        },
        "web": {},
        "logging": {"version": 1},
    }


@pytest.fixture
def probe_logging_config() -> Iterator[dict[str, Any]]:
    yield {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"plain": {"format": "%(message)s"}},
        "handlers": {
            "probe": {
                "class": "logging.NullHandler",
                "formatter": "plain",
                "level": "DEBUG",
            }
        },
        "loggers": {
            PROBE_LOGGER_NAME: {
                "level": "WARNING",
                "handlers": ["probe"],
                "propagate": False,
            }
        },
    }
    probe_logger = logging.getLogger(PROBE_LOGGER_NAME)
    probe_logger.handlers.clear()
    probe_logger.setLevel(logging.NOTSET)
    probe_logger.propagate = True


def test_load_config_reads_bundled_config() -> None:
    config = load_config(BUNDLED_CONFIG_PACKAGE)

    assert isinstance(config, AppConfig)
    assert config.model.name == "dummy-model-name"
    assert config.mcp["calculator"].is_oauth is False
    assert config.logging["version"] == 1


def test_load_config_returns_cached_instance() -> None:
    first = load_config(BUNDLED_CONFIG_PACKAGE)

    assert load_config(BUNDLED_CONFIG_PACKAGE) is first


def test_load_config_reads_package_config(
    make_package: PackageFactory, valid_config: dict[str, Any]
) -> None:
    package = make_package(yaml.safe_dump(valid_config))

    config = load_config(package)

    assert config.model.name == "test-model"
    assert config.model.api_style == "responses"


def test_load_config_rejects_invalid_yaml(
    make_package: PackageFactory,
) -> None:
    package = make_package("foundry: [unclosed")

    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(package)


@pytest.mark.parametrize(
    "config_text",
    ["", "- item\n", "just a string\n", "42\n"],
    ids=["empty", "list", "string", "number"],
)
def test_load_config_rejects_non_mapping_yaml(
    make_package: PackageFactory, config_text: str
) -> None:
    package = make_package(config_text)

    with pytest.raises(ValueError, match="Expected a YAML mapping"):
        load_config(package)


@pytest.mark.parametrize("section", ["azure", "foundry", "model", "logging"])
def test_load_config_rejects_missing_section(
    make_package: PackageFactory,
    valid_config: dict[str, Any],
    section: str,
) -> None:
    del valid_config[section]
    package = make_package(yaml.safe_dump(valid_config))

    with pytest.raises(ValidationError, match=section):
        load_config(package)


def test_load_config_defaults_missing_optional_sections(
    make_package: PackageFactory, valid_config: dict[str, Any]
) -> None:
    del valid_config["mcp"]
    del valid_config["web"]
    package = make_package(yaml.safe_dump(valid_config))

    config = load_config(package)

    assert config.mcp == {}
    assert config.web == Web()


def test_load_config_raises_when_config_file_missing(
    make_package: PackageFactory,
) -> None:
    package = make_package(None)

    with pytest.raises(FileNotFoundError):
        load_config(package)


def test_load_config_raises_when_package_missing() -> None:
    with pytest.raises(ModuleNotFoundError):
        load_config(f"missing_{uuid.uuid4().hex}")


def test_configure_logging_applies_logging_section(
    probe_logging_config: dict[str, Any],
) -> None:
    config = load_config(BUNDLED_CONFIG_PACKAGE).model_copy(
        update={"logging": probe_logging_config}
    )

    configure_logging(config)

    probe_logger = logging.getLogger(PROBE_LOGGER_NAME)
    assert probe_logger.level == logging.WARNING
    assert isinstance(probe_logger.handlers[0], logging.NullHandler)
    assert probe_logger.propagate is False


def test_configure_logging_leaves_config_unchanged(
    probe_logging_config: dict[str, Any],
) -> None:
    config = load_config(BUNDLED_CONFIG_PACKAGE).model_copy(
        update={"logging": probe_logging_config}
    )
    original = copy.deepcopy(config.logging)

    configure_logging(config)

    assert config.logging == original
