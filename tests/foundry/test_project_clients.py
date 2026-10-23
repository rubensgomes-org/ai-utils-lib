"""Tests for ai_utils_lib.foundry.project_clients."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ai_utils_lib.foundry.project_clients import get_ai_project_clients

MODULE = "ai_utils_lib.foundry.project_clients"
ENDPOINT = "https://test.services.ai.azure.com/api/projects/test-project"


@dataclass(frozen=True)
class FoundryMocks:
    credential: MagicMock
    project_client: MagicMock
    project_client_class: MagicMock
    openai_client: MagicMock


def _async_context_mock(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.__aenter__.return_value = mock
    return mock


@pytest.fixture
def foundry_mocks(mocker: MockerFixture) -> FoundryMocks:
    """Replace the credential, project and OpenAI clients with mocks."""
    credential = _async_context_mock(mocker)
    mocker.patch(f"{MODULE}.DefaultAzureCredential", return_value=credential)

    openai_client = _async_context_mock(mocker)
    project_client = _async_context_mock(mocker)
    project_client.get_openai_client.return_value = openai_client
    project_client_class = mocker.patch(
        f"{MODULE}.AIProjectClient", return_value=project_client
    )
    return FoundryMocks(
        credential, project_client, project_client_class, openai_client
    )


async def test_get_ai_project_clients_yields_open_clients(
    foundry_mocks: FoundryMocks,
) -> None:
    async with get_ai_project_clients(ENDPOINT) as clients:
        assert clients == (
            foundry_mocks.project_client,
            foundry_mocks.openai_client,
        )


async def test_get_ai_project_clients_connects_to_endpoint(
    foundry_mocks: FoundryMocks,
) -> None:
    async with get_ai_project_clients(ENDPOINT):
        pass

    foundry_mocks.project_client_class.assert_called_once_with(
        endpoint=ENDPOINT, credential=foundry_mocks.credential
    )


async def test_get_ai_project_clients_closes_clients_on_exit(
    foundry_mocks: FoundryMocks,
) -> None:
    async with get_ai_project_clients(ENDPOINT):
        pass

    _assert_all_closed(foundry_mocks)


async def test_get_ai_project_clients_closes_clients_on_error(
    foundry_mocks: FoundryMocks,
) -> None:
    with pytest.raises(RuntimeError):
        async with get_ai_project_clients(ENDPOINT):
            raise RuntimeError("consumer failed")

    _assert_all_closed(foundry_mocks)


def _assert_all_closed(foundry_mocks: FoundryMocks) -> None:
    foundry_mocks.openai_client.__aexit__.assert_awaited_once()
    foundry_mocks.project_client.__aexit__.assert_awaited_once()
    foundry_mocks.credential.__aexit__.assert_awaited_once()
