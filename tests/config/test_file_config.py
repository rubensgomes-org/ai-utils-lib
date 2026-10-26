"""Tests for ai_utils_lib.file.file_config."""

import copy
import logging
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

import ai_utils_lib
from ai_utils_lib.config_models import AppConfig, Web
from ai_utils_lib.file.file_config import configure_logging, load_config

BUNDLED_CONFIG = Path(ai_utils_lib.__file__).with_name("config.yaml")
PROBE_LOGGER_NAME = "tests.file.file_config.probe"

ConfigFactory = Callable[[str], Path]


@pytest.fixture(autouse=True)
def clear_config_cache() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


@pytest.fixture
def make_config(tmp_path: Path) -> ConfigFactory:
    """Write ``config_text`` to a ``config.yaml`` file in ``tmp_path``."""

    def factory(config_text: str) -> Path:
        config = tmp_path / "config.yaml"
        config.write_text(config_text, encoding="utf-8")
        return config

    return factory


@pytest.fixture
def valid_config() -> dict[str, Any]:
    return {
        "azure": {
            "app_config_prefix": "test-prefix/",
            "secret_prefix": "test-prefix",
            "secret_separator": "--",
        },
        "foundry": {
            "project_endpoint": "https://example.com/foundry",
            "resource_endpoint": "https://example.com/",
        },
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
    config = load_config(BUNDLED_CONFIG)

    assert isinstance(config, AppConfig)
    assert config.model.name == "dummy-model-name"
    assert config.mcp["calculator"].is_oauth is False
    assert config.logging["version"] == 1


def test_load_config_returns_cached_instance() -> None:
    first = load_config(BUNDLED_CONFIG)

    assert load_config(BUNDLED_CONFIG) is first


def test_load_config_reads_config_file(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.model.name == "test-model"
    assert config.model.api_style == "responses"


def test_load_config_rejects_invalid_yaml(
    make_config: ConfigFactory,
) -> None:
    config_file = make_config("foundry: [unclosed")

    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(config_file)


@pytest.mark.parametrize(
    "config_text",
    ["", "- item\n", "just a string\n", "42\n"],
    ids=["empty", "list", "string", "number"],
)
def test_load_config_rejects_non_mapping_yaml(
    make_config: ConfigFactory, config_text: str
) -> None:
    config_file = make_config(config_text)

    with pytest.raises(ValueError, match="Expected a YAML mapping"):
        load_config(config_file)


@pytest.mark.parametrize("section", ["foundry", "logging"])
def test_load_config_rejects_missing_section(
    make_config: ConfigFactory,
    valid_config: dict[str, Any],
    section: str,
) -> None:
    del valid_config[section]
    config_file = make_config(yaml.safe_dump(valid_config))

    with pytest.raises(ValidationError, match=section):
        load_config(config_file)


def test_load_config_defaults_missing_azure(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    del valid_config["azure"]
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.azure is None


def test_load_config_reads_foundry_agent_name(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    valid_config["foundry"]["agent_name"] = "test-agent"
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.foundry.agent_name == "test-agent"


def test_load_config_defaults_missing_foundry_agent_name(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.foundry.agent_name is None


def test_load_config_defaults_missing_foundry_project_endpoint(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    del valid_config["foundry"]["project_endpoint"]
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.foundry.project_endpoint is None


def test_load_config_defaults_missing_foundry_resource_endpoint(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    del valid_config["foundry"]["resource_endpoint"]
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.foundry.resource_endpoint is None


def test_load_config_rejects_empty_foundry_agent_name(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    valid_config["foundry"]["agent_name"] = ""
    config_file = make_config(yaml.safe_dump(valid_config))

    with pytest.raises(ValidationError, match="agent_name"):
        load_config(config_file)


def test_load_config_defaults_missing_optional_sections(
    make_config: ConfigFactory, valid_config: dict[str, Any]
) -> None:
    del valid_config["mcp"]
    del valid_config["model"]
    del valid_config["web"]
    config_file = make_config(yaml.safe_dump(valid_config))

    config = load_config(config_file)

    assert config.mcp == {}
    assert config.model is None
    assert config.web == Web()


def test_load_config_raises_when_config_file_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "config.yaml")


def test_configure_logging_applies_logging_section(
    probe_logging_config: dict[str, Any],
) -> None:
    config = load_config(BUNDLED_CONFIG).model_copy(
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
    config = load_config(BUNDLED_CONFIG).model_copy(
        update={"logging": probe_logging_config}
    )
    original = copy.deepcopy(config.logging)

    configure_logging(config)

    assert config.logging == original
