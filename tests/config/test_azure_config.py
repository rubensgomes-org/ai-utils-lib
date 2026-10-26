"""Tests for ai_utils_lib.azure.azure_config."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.appconfiguration import ConfigurationSetting
from pydantic import ValidationError
from pytest_mock import MockerFixture

import ai_utils_lib
from ai_utils_lib.azure.azure_config import aload_config
from ai_utils_lib.config_models import AppConfig
from ai_utils_lib.file.file_config import load_config as load_file_config

MODULE = "ai_utils_lib.azure.azure_config"
BUNDLED_CONFIG = Path(ai_utils_lib.__file__).with_name("config.yaml")
ENDPOINT = "https://appcs-test.azconfig.io"
PREFIX = "ai-utils-lib/"
LABEL_FILTER = "lab"
VAULT_URL = "https://kv-test.vault.azure.net/"
# secret_prefix + secret_separator + dashed api_key_env of the bundled
# config.yaml
SECRET_NAME = "ai-utils-lib--NVIDIA-API-KEY"
SECRET_VALUE = "kv-secret"
API_KEY_ENV = "NVIDIA_API_KEY"


@pytest.fixture(autouse=True)
def clear_config_cache() -> Iterator[None]:
    load_file_config.cache_clear()
    yield
    load_file_config.cache_clear()


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


@pytest.fixture
def app_config() -> AppConfig:
    return load_file_config(BUNDLED_CONFIG)


def _setting(key: str, value: str) -> ConfigurationSetting:
    return ConfigurationSetting(key=f"{PREFIX}{key}", value=value)


def _with_prefix(app_config: AppConfig, prefix: str) -> AppConfig:
    assert app_config.azure is not None
    azure = app_config.azure.model_copy(update={"app_config_prefix": prefix})
    return app_config.model_copy(update={"azure": azure})


async def test_aload_config_queries_store_with_prefix_and_label(
    app_config: AppConfig,
    list_settings_mock: AsyncMock,
    credential_mock: MagicMock,
) -> None:
    await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    list_settings_mock.assert_awaited_once_with(
        credential_mock, ENDPOINT, f"{PREFIX}*", LABEL_FILTER
    )


async def test_aload_config_overrides_yaml_with_settings(
    app_config: AppConfig, list_settings_mock: AsyncMock
) -> None:
    list_settings_mock.return_value = [
        _setting("model/name", "azure-model"),
        _setting("model/temperature", "0.5"),
        _setting("mcp/calculator/is_oauth", "true"),
        _setting("web/port", "9999"),
    ]

    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    assert config.model.name == "azure-model"
    assert config.model.temperature == 0.5
    assert config.mcp["calculator"].is_oauth is True
    assert config.web.port == 9999
    assert config.model.api_style == "responses"


async def test_aload_config_adds_new_mcp_server(
    app_config: AppConfig, list_settings_mock: AsyncMock
) -> None:
    list_settings_mock.return_value = [
        _setting("mcp/weather/url", "https://example.com/mcp"),
        _setting("mcp/weather/token_dir", "~/.weather"),
    ]

    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    assert config.mcp["weather"].token_dir == "~/.weather"
    assert "calculator" in config.mcp


async def test_aload_config_rejects_unknown_setting(
    app_config: AppConfig, list_settings_mock: AsyncMock
) -> None:
    list_settings_mock.return_value = [_setting("model/temprature", "0.5")]

    with pytest.raises(ValidationError, match="temprature"):
        await aload_config(app_config, ENDPOINT, LABEL_FILTER)


@pytest.mark.parametrize(
    "keys", [("model", "model/name"), ("model/name", "model")]
)
async def test_aload_config_rejects_setting_conflicting_with_section(
    app_config: AppConfig,
    list_settings_mock: AsyncMock,
    keys: tuple[str, str],
) -> None:
    list_settings_mock.return_value = [_setting(key, "value") for key in keys]

    with pytest.raises(ValueError, match="conflicts"):
        await aload_config(app_config, ENDPOINT, LABEL_FILTER)


async def test_aload_config_names_secret_with_overridden_secret_prefix(
    app_config: AppConfig,
    list_settings_mock: AsyncMock,
    read_secret_mock: AsyncMock,
    credential_mock: MagicMock,
) -> None:
    list_settings_mock.return_value = [_setting("azure/secret_prefix", "kv")]

    await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_awaited_once_with(
        credential_mock, VAULT_URL, "kv--NVIDIA-API-KEY"
    )


async def test_aload_config_completes_prefix_with_separator(
    app_config: AppConfig,
    list_settings_mock: AsyncMock,
    credential_mock: MagicMock,
) -> None:
    app_config = _with_prefix(app_config, PREFIX.removesuffix("/"))
    list_settings_mock.return_value = [_setting("model/name", "azure-model")]

    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    list_settings_mock.assert_awaited_once_with(
        credential_mock, ENDPOINT, f"{PREFIX}*", LABEL_FILTER
    )
    assert config.model.name == "azure-model"


@pytest.mark.parametrize("key", ["/model/name", "model//name", "model/"])
async def test_aload_config_rejects_setting_with_empty_segment(
    app_config: AppConfig, list_settings_mock: AsyncMock, key: str
) -> None:
    list_settings_mock.return_value = [_setting(key, "value")]

    with pytest.raises(ValueError, match="empty segment"):
        await aload_config(app_config, ENDPOINT, LABEL_FILTER)


@pytest.mark.usefixtures("list_settings_mock")
async def test_aload_config_reads_api_key_from_key_vault(
    app_config: AppConfig,
    read_secret_mock: AsyncMock,
    credential_mock: MagicMock,
) -> None:
    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_awaited_once_with(
        credential_mock, VAULT_URL, SECRET_NAME
    )
    assert config.model.api_key == SECRET_VALUE
    credential_mock.__aexit__.assert_awaited_once()


@pytest.mark.usefixtures("list_settings_mock")
async def test_aload_config_prefers_api_key_env_over_key_vault(
    app_config: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
    read_secret_mock: AsyncMock,
) -> None:
    monkeypatch.setenv(API_KEY_ENV, "env-secret")

    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()
    assert config.model.api_key == "env-secret"


async def test_aload_config_skips_key_vault_without_api_key_env(
    app_config: AppConfig,
    list_settings_mock: AsyncMock,
    read_secret_mock: AsyncMock,
) -> None:
    list_settings_mock.return_value = [_setting("model/api_key_env", "")]

    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()
    assert config.model.api_key is None


@pytest.mark.usefixtures("list_settings_mock")
async def test_aload_config_skips_key_vault_without_model_section(
    app_config: AppConfig, read_secret_mock: AsyncMock
) -> None:
    app_config = app_config.model_copy(update={"model": None})

    config = await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()
    assert config.model is None


@pytest.mark.usefixtures("list_settings_mock")
async def test_aload_config_requires_key_vault_uri(
    app_config: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
    read_secret_mock: AsyncMock,
) -> None:
    monkeypatch.delenv("KEY_VAULT_URI")

    with pytest.raises(RuntimeError, match=f"KEY_VAULT_URI.*{SECRET_NAME}"):
        await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    read_secret_mock.assert_not_called()


async def test_aload_config_escapes_prefix_in_key_filter(
    app_config: AppConfig,
    list_settings_mock: AsyncMock,
    credential_mock: MagicMock,
) -> None:
    app_config = _with_prefix(app_config, "a*b,c\\d/")

    await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    list_settings_mock.assert_awaited_once_with(
        credential_mock, ENDPOINT, "a\\*b\\,c\\\\d/*", LABEL_FILTER
    )


async def test_aload_config_rejects_setting_without_value(
    app_config: AppConfig, list_settings_mock: AsyncMock
) -> None:
    key = f"{PREFIX}model/temperature"
    list_settings_mock.return_value = [ConfigurationSetting(key=key)]

    with pytest.raises(ValueError, match=f"{key} has no value"):
        await aload_config(app_config, ENDPOINT, LABEL_FILTER)


async def test_aload_config_requires_azure_section(
    app_config: AppConfig, list_settings_mock: AsyncMock
) -> None:
    app_config = app_config.model_copy(update={"azure": None})

    with pytest.raises(ValueError, match="azure config section"):
        await aload_config(app_config, ENDPOINT, LABEL_FILTER)

    list_settings_mock.assert_not_called()
