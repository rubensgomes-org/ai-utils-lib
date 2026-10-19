"""Tests for ai_utils_lib.config.azure.config."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.appconfiguration import ConfigurationSetting
from pytest_mock import MockerFixture

from ai_utils_lib.config.azure.config import load_config

MODULE = "ai_utils_lib.config.azure.config"
BUNDLED_CONFIG_PACKAGE = "ai_utils_lib.config"
ENDPOINT = "https://appcs-test.azconfig.io"
PREFIX = "ai-utils/"
LABEL_FILTER = "lab"
VAULT_URL = "https://kv-test.vault.azure.net/"
# secret_prefix + secret_separator + dashed api_key_env of the bundled
# config.yaml
SECRET_NAME = "dummy-kv-prefix--DUMMY-API-KEY"
SECRET_VALUE = "kv-secret"
API_KEY_ENV = "DUMMY_API_KEY"


@pytest.fixture(autouse=True)
def clear_config_cache() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


@pytest.fixture
def list_settings_mock(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch(f"{MODULE}.list_settings", return_value=[])


@pytest.fixture(autouse=True)
def credential_mock(mocker: MockerFixture) -> MagicMock:
    credential = mocker.MagicMock()
    credential.__aenter__.return_value = credential
    mocker.patch(f"{MODULE}.DefaultAzureCredential", return_value=credential)
    return credential


@pytest.fixture(autouse=True)
def read_secret_mock(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> AsyncMock:
    monkeypatch.setenv("KEY_VAULT_URI", VAULT_URL)
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    return mocker.patch(f"{MODULE}.read_secret", return_value=SECRET_VALUE)


def _setting(key: str, value: str) -> ConfigurationSetting:
    return ConfigurationSetting(key=f"{PREFIX}{key}", value=value)


def test_load_config_queries_store_with_prefix_and_label(
    list_settings_mock: AsyncMock, credential_mock: MagicMock
) -> None:
    load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    list_settings_mock.assert_awaited_once_with(
        credential_mock, ENDPOINT, f"{PREFIX}*", LABEL_FILTER
    )


def test_load_config_overrides_yaml_with_settings(
    list_settings_mock: AsyncMock,
) -> None:
    list_settings_mock.return_value = [
        _setting("model/name", "azure-model"),
        _setting("model/temperature", "0.5"),
        _setting("mcp/calculator/is_oauth", "true"),
        _setting("web/port", "9999"),
    ]

    config = load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    assert config.model.name == "azure-model"
    assert config.model.temperature == 0.5
    assert config.mcp["calculator"].is_oauth is True
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


@pytest.mark.usefixtures("list_settings_mock")
def test_load_config_reads_api_key_from_key_vault(
    read_secret_mock: AsyncMock, credential_mock: MagicMock
) -> None:
    config = load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_awaited_once_with(
        credential_mock, VAULT_URL, SECRET_NAME
    )
    assert config.model.api_key == SECRET_VALUE
    credential_mock.__aexit__.assert_awaited_once()


@pytest.mark.usefixtures("list_settings_mock")
def test_load_config_prefers_api_key_env_over_key_vault(
    monkeypatch: pytest.MonkeyPatch, read_secret_mock: AsyncMock
) -> None:
    monkeypatch.setenv(API_KEY_ENV, "env-secret")

    config = load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()
    assert config.model.api_key == "env-secret"


def test_load_config_skips_key_vault_without_api_key_env(
    list_settings_mock: AsyncMock, read_secret_mock: AsyncMock
) -> None:
    list_settings_mock.return_value = [_setting("model/api_key_env", "")]

    config = load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()
    assert config.model.api_key is None


@pytest.mark.usefixtures("list_settings_mock")
def test_load_config_requires_key_vault_uri(
    monkeypatch: pytest.MonkeyPatch, read_secret_mock: AsyncMock
) -> None:
    monkeypatch.delenv("KEY_VAULT_URI")

    with pytest.raises(KeyError, match=f"KEY_VAULT_URI.*{SECRET_NAME}"):
        load_config(BUNDLED_CONFIG_PACKAGE, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()
