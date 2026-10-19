"""Tests for ai_utils_lib.config.azure.app_configuration."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from azure.appconfiguration import ConfigurationSetting
from azure.core.exceptions import HttpResponseError
from pytest_mock import MockerFixture

from ai_utils_lib.config.azure.app_configuration import list_settings

MODULE = "ai_utils_lib.config.azure.app_configuration"
ENDPOINT = "https://appcs-test.azconfig.io"
KEY_FILTER = "ca-test/*"
LABEL_FILTER = "dev"


@dataclass(frozen=True)
class AzureMocks:
    credential: MagicMock
    client: MagicMock
    client_class: MagicMock


@pytest.fixture
def azure_mocks(mocker: MockerFixture) -> AzureMocks:
    """Replace the App Configuration client with a mock."""
    credential = mocker.MagicMock()

    client = mocker.MagicMock()
    client.__aenter__.return_value = client
    client_class = mocker.patch(
        f"{MODULE}.AzureAppConfigurationClient", return_value=client
    )
    return AzureMocks(credential, client, client_class)


def _return_settings(
    client: MagicMock, settings: list[ConfigurationSetting]
) -> None:
    client.list_configuration_settings.return_value.__aiter__.return_value = (
        settings
    )


async def test_list_settings_returns_all_settings(
    azure_mocks: AzureMocks,
) -> None:
    settings = [
        ConfigurationSetting(key="ca-test/one", value="1"),
        ConfigurationSetting(key="ca-test/two", value="2"),
    ]
    _return_settings(azure_mocks.client, settings)

    result = await list_settings(
        azure_mocks.credential, ENDPOINT, KEY_FILTER, LABEL_FILTER
    )

    assert result == settings


async def test_list_settings_returns_empty_list_when_none_match(
    azure_mocks: AzureMocks,
) -> None:
    _return_settings(azure_mocks.client, [])

    assert (
        await list_settings(
            azure_mocks.credential, ENDPOINT, KEY_FILTER, LABEL_FILTER
        )
        == []
    )


async def test_list_settings_queries_store_with_filters(
    azure_mocks: AzureMocks,
) -> None:
    _return_settings(azure_mocks.client, [])

    await list_settings(
        azure_mocks.credential, ENDPOINT, KEY_FILTER, LABEL_FILTER
    )

    azure_mocks.client_class.assert_called_once_with(
        ENDPOINT, azure_mocks.credential
    )
    azure_mocks.client.list_configuration_settings.assert_called_once_with(
        key_filter=KEY_FILTER, label_filter=LABEL_FILTER
    )


async def test_list_settings_closes_client(
    azure_mocks: AzureMocks,
) -> None:
    _return_settings(azure_mocks.client, [])

    await list_settings(
        azure_mocks.credential, ENDPOINT, KEY_FILTER, LABEL_FILTER
    )

    azure_mocks.client.__aexit__.assert_awaited_once()
    azure_mocks.credential.close.assert_not_called()


async def test_list_settings_closes_client_when_listing_fails(
    azure_mocks: AzureMocks,
) -> None:
    azure_mocks.client.list_configuration_settings.side_effect = (
        HttpResponseError("Forbidden")
    )

    with pytest.raises(HttpResponseError, match="Forbidden"):
        await list_settings(
            azure_mocks.credential, ENDPOINT, KEY_FILTER, LABEL_FILTER
        )

    azure_mocks.client.__aexit__.assert_awaited_once()
    azure_mocks.credential.close.assert_not_called()
