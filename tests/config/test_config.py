"""Tests for ai_utils_lib.config."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.appconfiguration import ConfigurationSetting
from pytest_mock import MockerFixture

import ai_utils_lib
from ai_utils_lib.config import aload_config
from ai_utils_lib.file.file_load_config import load_config as _load_file_config

AZURE_MODULE = "ai_utils_lib.azure.azure_load_config"
BUNDLED_CONFIG = Path(ai_utils_lib.__file__).with_name("config.yaml")
ENDPOINT = "https://appcs-test.azconfig.io"
PREFIX = "ai-utils-lib/"
LABEL = "lab"
VAULT_URL = "https://kv-test.vault.azure.net/"


@pytest.fixture(autouse=True)
def clear_config_cache() -> Iterator[None]:
    _load_file_config.cache_clear()
    yield
    _load_file_config.cache_clear()


@pytest.fixture
def list_settings_mock(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch(f"{AZURE_MODULE}.list_settings", return_value=[])


@pytest.fixture
def credential_mock(mocker: MockerFixture) -> MagicMock:
    credential = mocker.MagicMock()
    credential.__aenter__.return_value = credential
    mocker.patch(
        f"{AZURE_MODULE}.DefaultAzureCredential", return_value=credential
    )
    return credential


@pytest.fixture
def read_secret_mock(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch(f"{AZURE_MODULE}.read_secret", return_value="kv-secret")


@pytest.fixture
def azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_CONFIG_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("APP_ENV", LABEL)
    monkeypatch.setenv("KEY_VAULT_URI", VAULT_URL)


@pytest.fixture
def local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_CONFIG_ENDPOINT", raising=False)


@pytest.mark.usefixtures("azure_env", "read_secret_mock")
async def test_aload_config_reads_app_configuration_in_azure(
    list_settings_mock: AsyncMock, credential_mock: MagicMock
) -> None:
    list_settings_mock.return_value = [
        ConfigurationSetting(key=f"{PREFIX}model/name", value="azure-model")
    ]

    config = await aload_config(BUNDLED_CONFIG)

    list_settings_mock.assert_awaited_once_with(
        credential_mock, ENDPOINT, f"{PREFIX}*", LABEL
    )
    assert config.model.name == "azure-model"


@pytest.mark.usefixtures("local_env")
async def test_aload_config_reads_yaml_only_locally(
    list_settings_mock: AsyncMock,
) -> None:
    config = await aload_config(BUNDLED_CONFIG)

    list_settings_mock.assert_not_called()
    assert config.model.name == "dummy-model-name"


@pytest.mark.usefixtures("local_env")
async def test_aload_config_treats_empty_endpoint_as_local(
    monkeypatch: pytest.MonkeyPatch, list_settings_mock: AsyncMock
) -> None:
    monkeypatch.setenv("APP_CONFIG_ENDPOINT", "")

    await aload_config(BUNDLED_CONFIG)

    list_settings_mock.assert_not_called()


@pytest.mark.usefixtures("azure_env")
@pytest.mark.parametrize("app_env", [None, ""])
async def test_aload_config_requires_app_env_in_azure(
    monkeypatch: pytest.MonkeyPatch,
    list_settings_mock: AsyncMock,
    app_env: str | None,
) -> None:
    if app_env is None:
        monkeypatch.delenv("APP_ENV")
    else:
        monkeypatch.setenv("APP_ENV", app_env)

    with pytest.raises(RuntimeError, match="APP_ENV must be set"):
        await aload_config(BUNDLED_CONFIG)

    list_settings_mock.assert_not_called()
