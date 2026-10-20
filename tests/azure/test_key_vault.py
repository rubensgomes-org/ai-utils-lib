"""Tests for ai_utils_lib.azure.key_vault."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError
from pytest_mock import MockerFixture

from ai_utils_lib.azure.key_vault import read_secret

MODULE = "ai_utils_lib.azure.key_vault"
VAULT_URL = "https://kv-test.vault.azure.net/"
SECRET_NAME = "test-api-key"
SECRET_VALUE = "test-secret-value"


@dataclass(frozen=True)
class AzureMocks:
    credential: MagicMock
    client: MagicMock
    client_class: MagicMock


@pytest.fixture
def azure_mocks(mocker: MockerFixture) -> AzureMocks:
    """Replace the Key Vault client with a mock."""
    credential = mocker.MagicMock()

    client = mocker.MagicMock()
    client.__aenter__.return_value = client
    client.get_secret = mocker.AsyncMock()
    client_class = mocker.patch(f"{MODULE}.SecretClient", return_value=client)
    return AzureMocks(credential, client, client_class)


def _return_secret(client: MagicMock, value: str | None) -> None:
    client.get_secret.return_value = MagicMock(value=value)


async def test_read_secret_returns_secret_value(
    azure_mocks: AzureMocks,
) -> None:
    _return_secret(azure_mocks.client, SECRET_VALUE)

    assert (
        await read_secret(azure_mocks.credential, VAULT_URL, SECRET_NAME)
        == SECRET_VALUE
    )


async def test_read_secret_requests_secret_from_vault(
    azure_mocks: AzureMocks,
) -> None:
    _return_secret(azure_mocks.client, SECRET_VALUE)

    await read_secret(azure_mocks.credential, VAULT_URL, SECRET_NAME)

    azure_mocks.client_class.assert_called_once_with(
        vault_url=VAULT_URL, credential=azure_mocks.credential
    )
    azure_mocks.client.get_secret.assert_awaited_once_with(SECRET_NAME)


async def test_read_secret_strips_surrounding_whitespace(
    azure_mocks: AzureMocks,
) -> None:
    _return_secret(azure_mocks.client, f" {SECRET_VALUE}\n")

    assert (
        await read_secret(azure_mocks.credential, VAULT_URL, SECRET_NAME)
        == SECRET_VALUE
    )


@pytest.mark.parametrize(
    "value", ["", None, " \n"], ids=["empty", "none", "blank"]
)
async def test_read_secret_rejects_empty_secret(
    azure_mocks: AzureMocks, value: str | None
) -> None:
    _return_secret(azure_mocks.client, value)

    with pytest.raises(ValueError, match=f"{SECRET_NAME} .* is empty"):
        await read_secret(azure_mocks.credential, VAULT_URL, SECRET_NAME)


async def test_read_secret_closes_client(
    azure_mocks: AzureMocks,
) -> None:
    _return_secret(azure_mocks.client, SECRET_VALUE)

    await read_secret(azure_mocks.credential, VAULT_URL, SECRET_NAME)

    azure_mocks.client.__aexit__.assert_awaited_once()
    azure_mocks.credential.close.assert_not_called()


async def test_read_secret_closes_client_when_secret_missing(
    azure_mocks: AzureMocks,
) -> None:
    azure_mocks.client.get_secret.side_effect = ResourceNotFoundError(
        "SecretNotFound"
    )

    with pytest.raises(ResourceNotFoundError, match="SecretNotFound"):
        await read_secret(azure_mocks.credential, VAULT_URL, SECRET_NAME)

    azure_mocks.client.__aexit__.assert_awaited_once()
    azure_mocks.credential.close.assert_not_called()


@pytest.mark.parametrize(
    "secret_name",
    ["", "bad_name", "bad.name", "a" * 128],
    ids=["empty", "underscore", "dot", "too-long"],
)
async def test_read_secret_rejects_invalid_secret_name(
    azure_mocks: AzureMocks, secret_name: str
) -> None:
    with pytest.raises(ValueError, match="1-127 alphanumerics or dashes"):
        await read_secret(azure_mocks.credential, VAULT_URL, secret_name)

    azure_mocks.client_class.assert_not_called()
