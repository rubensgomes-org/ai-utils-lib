"""Tests for ai_utils_lib.config.config."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from azure.appconfiguration import ConfigurationSetting
from pytest_mock import MockerFixture

from ai_utils_lib.config.azure.config import load_config as load_azure_config
from ai_utils_lib.config.config import load_config
from ai_utils_lib.config.file.config import load_config as load_file_config

AZURE_MODULE = "ai_utils_lib.config.azure.config"
BUNDLED_CONFIG_PACKAGE = "ai_utils_lib.config"
ENDPOINT = "https://appcs-test.azconfig.io"
PREFIX = "ai-utils"
LABEL = "lab"


@pytest.fixture(autouse=True)
def clear_config_caches() -> Iterator[None]:
    load_azure_config.cache_clear()
    load_file_config.cache_clear()
    yield
    load_azure_config.cache_clear()
    load_file_config.cache_clear()


@pytest.fixture
def list_settings_mock(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch(f"{AZURE_MODULE}.list_settings", return_value=[])


@pytest.fixture
def azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_CONFIG_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("APP_ENV", LABEL)


@pytest.fixture
def local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_CONFIG_ENDPOINT", raising=False)


@pytest.mark.usefixtures("azure_env")
def test_load_config_reads_app_configuration_in_azure(
    list_settings_mock: AsyncMock,
) -> None:
    list_settings_mock.return_value = [
        ConfigurationSetting(key=f"{PREFIX}model/name", value="azure-model")
    ]

    config = load_config(BUNDLED_CONFIG_PACKAGE)

    list_settings_mock.assert_awaited_once_with(ENDPOINT, f"{PREFIX}*", LABEL)
    assert config.model.name == "azure-model"


@pytest.mark.usefixtures("local_env")
def test_load_config_reads_yaml_only_locally(
    list_settings_mock: AsyncMock,
) -> None:
    config = load_config(BUNDLED_CONFIG_PACKAGE)

    list_settings_mock.assert_not_called()
    assert config.model.name == "dummy-model-name"


@pytest.mark.usefixtures("local_env")
def test_load_config_treats_empty_endpoint_as_local(
    monkeypatch: pytest.MonkeyPatch, list_settings_mock: AsyncMock
) -> None:
    monkeypatch.setenv("APP_CONFIG_ENDPOINT", "")

    load_config(BUNDLED_CONFIG_PACKAGE)

    list_settings_mock.assert_not_called()


@pytest.mark.usefixtures("azure_env")
def test_load_config_requires_app_env_in_azure(
    monkeypatch: pytest.MonkeyPatch, list_settings_mock: AsyncMock
) -> None:
    monkeypatch.delenv("APP_ENV")

    with pytest.raises(KeyError, match="APP_ENV"):
        load_config(BUNDLED_CONFIG_PACKAGE)

    list_settings_mock.assert_not_called()
