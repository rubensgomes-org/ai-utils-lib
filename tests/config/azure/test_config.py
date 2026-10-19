"""Tests for ai_utils_lib.config.azure.config."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from azure.appconfiguration import ConfigurationSetting
from pytest_mock import MockerFixture

from ai_utils_lib.config.azure.config import load_config

MODULE = "ai_utils_lib.config.azure.config"
BUNDLED_CONFIG_PACKAGE = "ai_utils_lib.config"
ENDPOINT = "https://appcs-test.azconfig.io"
PREFIX = "ai-utils-lib/"
LABEL_FILTER = "lab"


@pytest.fixture(autouse=True)
def clear_config_cache() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


@pytest.fixture
def list_settings_mock(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch(f"{MODULE}.list_settings", return_value=[])


def _setting(key: str, value: str) -> ConfigurationSetting:
    return ConfigurationSetting(key=f"{PREFIX}{key}", value=value)


def test_load_config_queries_store_with_prefix_and_label(
    list_settings_mock: AsyncMock,
) -> None:
    load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    list_settings_mock.assert_awaited_once_with(
        ENDPOINT, f"{PREFIX}*", LABEL_FILTER
    )


def test_load_config_overrides_yaml_with_settings(
    list_settings_mock: AsyncMock,
) -> None:
    list_settings_mock.return_value = [
        _setting("model/name", "azure-model"),
        _setting("model/temperature", "0.5"),
        _setting("mcp/calculator/is_oauth", "false"),
        _setting("web/port", "9999"),
    ]

    config = load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    assert config.model.name == "azure-model"
    assert config.model.temperature == 0.5
    assert config.mcp["calculator"].is_oauth is False
    assert config.web.port == 9999
    assert config.model.api_style == "responses"


def test_load_config_adds_new_mcp_server(
    list_settings_mock: AsyncMock,
) -> None:
    list_settings_mock.return_value = [
        _setting("mcp/weather/url", "https://example.com/mcp"),
        _setting("mcp/weather/token_dir", "~/.weather"),
    ]

    config = load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    assert config.mcp["weather"].token_dir == "~/.weather"
    assert "calculator" in config.mcp


def test_load_config_rejects_setting_conflicting_with_section(
    list_settings_mock: AsyncMock,
) -> None:
    list_settings_mock.return_value = [
        _setting("model", "flat"),
        _setting("model/name", "nested"),
    ]

    with pytest.raises(ValueError, match="conflicts"):
        load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)
