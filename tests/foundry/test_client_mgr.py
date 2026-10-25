"""Tests for ai_utils_lib.foundry.client_mgr."""

import logging
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from openai.types.responses import ResponseInputItemParam
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from ai_utils_lib.foundry.client_mgr import AIClientManager

MODULE = "ai_utils_lib.foundry.client_mgr"
LOGGER_NAME = "ai_utils_lib.foundry"
MAX_RETRIES = 5
ENDPOINT = "https://test.services.ai.azure.com/api/projects/test-project"
AGENT_NAME = "test-agent"
CONVERSATION_ID = "conv-123"
USER_MSG = "Hello, agent"
USER_ITEM: ResponseInputItemParam = {
    "type": "message",
    "role": "user",
    "content": USER_MSG,
}
CLIENT_PROPERTIES = ["project_client", "openai_client"]


@dataclass(frozen=True)
class FoundryMocks:
    credential: MagicMock
    project_client: MagicMock
    project_client_class: MagicMock
    openai_client: MagicMock
    agent_details: MagicMock
    response: MagicMock
    items_list: MagicMock
    conversation_items: list[MagicMock]


def _async_context_mock(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = False
    return mock


@pytest.fixture
def foundry_mocks(mocker: MockerFixture) -> FoundryMocks:
    """Replace the credential, project and OpenAI clients with mocks."""
    credential = _async_context_mock(mocker)
    mocker.patch(f"{MODULE}.DefaultAzureCredential", return_value=credential)

    agent_details = mocker.MagicMock()
    agent_details.name = AGENT_NAME
    agent_details.as_dict.return_value = {"name": AGENT_NAME}
    response = mocker.MagicMock()
    items_list = mocker.MagicMock()

    openai_client = _async_context_mock(mocker)
    openai_client.conversations.items.create = mocker.AsyncMock(
        return_value=items_list
    )
    openai_client.responses.create = mocker.AsyncMock(return_value=response)
    conversation_items = [mocker.MagicMock(), mocker.MagicMock()]
    item_pages = openai_client.conversations.items.list.return_value
    item_pages.__aiter__.return_value = conversation_items

    project_client = _async_context_mock(mocker)
    project_client.get_openai_client.return_value = openai_client
    project_client.agents.get = mocker.AsyncMock(return_value=agent_details)
    project_client_class = mocker.patch(
        f"{MODULE}.AIProjectClient", return_value=project_client
    )
    return FoundryMocks(
        credential,
        project_client,
        project_client_class,
        openai_client,
        agent_details,
        response,
        items_list,
        conversation_items,
    )


@pytest.fixture
def manager() -> AIClientManager:
    return AIClientManager(HttpUrl(ENDPOINT))


async def test_initialize_exposes_open_clients(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    assert manager.project_client is foundry_mocks.project_client
    assert manager.openai_client is foundry_mocks.openai_client


async def test_initialize_keeps_clients_open(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    foundry_mocks.openai_client.__aexit__.assert_not_awaited()
    foundry_mocks.project_client.__aexit__.assert_not_awaited()
    foundry_mocks.credential.__aexit__.assert_not_awaited()


async def test_initialize_connects_to_endpoint_as_string(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    foundry_mocks.project_client_class.assert_called_once_with(
        endpoint=ENDPOINT, credential=foundry_mocks.credential
    )


@pytest.mark.usefixtures("foundry_mocks")
async def test_initialize_twice_raises(manager: AIClientManager) -> None:
    await manager.initialize()

    with pytest.raises(RuntimeError, match="already initialized"):
        await manager.initialize()


async def test_initialize_failure_closes_opened_clients(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    foundry_mocks.openai_client.__aenter__.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await manager.initialize()

    foundry_mocks.project_client.__aexit__.assert_awaited_once()
    foundry_mocks.credential.__aexit__.assert_awaited_once()
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = manager.project_client


@pytest.mark.parametrize("client_property", CLIENT_PROPERTIES)
def test_client_access_before_initialize_raises(
    manager: AIClientManager, client_property: str
) -> None:
    with pytest.raises(RuntimeError, match="not initialized"):
        getattr(manager, client_property)


async def test_close_closes_all_clients(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()
    await manager.close()

    foundry_mocks.openai_client.__aexit__.assert_awaited_once()
    foundry_mocks.project_client.__aexit__.assert_awaited_once()
    foundry_mocks.credential.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("client_property", CLIENT_PROPERTIES)
@pytest.mark.usefixtures("foundry_mocks")
async def test_client_access_after_close_raises(
    manager: AIClientManager, client_property: str
) -> None:
    await manager.initialize()
    await manager.close()

    with pytest.raises(RuntimeError, match="not initialized"):
        getattr(manager, client_property)


async def test_close_twice_closes_clients_once(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()
    await manager.close()
    await manager.close()

    foundry_mocks.openai_client.__aexit__.assert_awaited_once()


async def test_close_before_initialize_is_noop(
    manager: AIClientManager,
) -> None:
    await manager.close()


async def test_initialize_after_close_reopens_clients(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()
    await manager.close()
    await manager.initialize()

    assert manager.openai_client is foundry_mocks.openai_client


async def test_save_user_msg_to_conversation_saves_user_message(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    items_list = await manager.save_user_msg_to_conversation(
        CONVERSATION_ID, USER_MSG
    )

    assert items_list is foundry_mocks.items_list
    create_items = foundry_mocks.openai_client.conversations.items.create
    create_items.assert_awaited_once_with(
        conversation_id=CONVERSATION_ID, items=[USER_ITEM]
    )


async def test_save_items_to_conversation_saves_items(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    items: list[ResponseInputItemParam] = [
        USER_ITEM,
        {"type": "message", "role": "assistant", "content": "Hi"},
    ]
    await manager.initialize()

    items_list = await manager.save_items_to_conversation(
        CONVERSATION_ID, items
    )

    assert items_list is foundry_mocks.items_list
    create_items = foundry_mocks.openai_client.conversations.items.create
    create_items.assert_awaited_once_with(
        conversation_id=CONVERSATION_ID, items=items
    )


async def test_post_conversation_to_agent_returns_response(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    response = await manager.post_conversation_to_agent(
        CONVERSATION_ID, AGENT_NAME
    )

    assert response is foundry_mocks.response


async def test_post_conversation_to_agent_routes_through_agent(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    await manager.post_conversation_to_agent(CONVERSATION_ID, AGENT_NAME)

    foundry_mocks.openai_client.responses.create.assert_awaited_once_with(
        conversation=CONVERSATION_ID,
        extra_body={
            "agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}
        },
        input="",
    )


async def test_fetch_agent_returns_named_agent(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    agent_details = await manager.fetch_agent(AGENT_NAME)

    assert agent_details is foundry_mocks.agent_details
    foundry_mocks.project_client.agents.get.assert_awaited_once_with(
        agent_name=AGENT_NAME
    )


async def test_fetch_agent_propagates_lookup_failure(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    foundry_mocks.project_client.agents.get.side_effect = LookupError("gone")
    await manager.initialize()

    with pytest.raises(LookupError, match="gone"):
        await manager.fetch_agent(AGENT_NAME)


async def test_initialize_sets_openai_max_retries(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    foundry_mocks.project_client.get_openai_client.assert_called_once_with(
        max_retries=MAX_RETRIES
    )


async def test_fetch_conversation_returns_all_items(
    manager: AIClientManager, foundry_mocks: FoundryMocks
) -> None:
    await manager.initialize()

    items = await manager.fetch_conversation(CONVERSATION_ID)

    assert items == foundry_mocks.conversation_items
    list_items = foundry_mocks.openai_client.conversations.items.list
    list_items.assert_called_once_with(conversation_id=CONVERSATION_ID)


@pytest.mark.usefixtures("foundry_mocks")
async def test_save_items_to_conversation_logs_items_at_debug(
    manager: AIClientManager, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    await manager.initialize()

    await manager.save_items_to_conversation(CONVERSATION_ID, [USER_ITEM])

    assert USER_MSG in caplog.text


@pytest.mark.usefixtures("foundry_mocks")
async def test_fetch_agent_logs_agent_details_at_debug(
    manager: AIClientManager, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    await manager.initialize()

    await manager.fetch_agent(AGENT_NAME)

    assert f'"name": "{AGENT_NAME}"' in caplog.text


async def test_debuglog_conversation_logs_items_at_debug(
    manager: AIClientManager,
    foundry_mocks: FoundryMocks,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for item in foundry_mocks.conversation_items:
        item.model_dump.return_value = {"content": USER_MSG}
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    await manager.initialize()

    await manager.debuglog_conversation(CONVERSATION_ID)

    assert USER_MSG in caplog.text


async def test_debuglog_conversation_skips_fetch_above_debug(
    manager: AIClientManager,
    foundry_mocks: FoundryMocks,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    await manager.initialize()

    await manager.debuglog_conversation(CONVERSATION_ID)

    foundry_mocks.openai_client.conversations.items.list.assert_not_called()


@pytest.mark.parametrize(
    "method, args",
    [
        ("save_user_msg_to_conversation", (CONVERSATION_ID, USER_MSG)),
        ("save_items_to_conversation", (CONVERSATION_ID, [USER_ITEM])),
        ("fetch_agent", (AGENT_NAME,)),
        ("fetch_conversation", (CONVERSATION_ID,)),
        ("post_conversation_to_agent", (CONVERSATION_ID, AGENT_NAME)),
    ],
)
async def test_client_methods_before_initialize_raise(
    manager: AIClientManager, method: str, args: tuple[object, ...]
) -> None:
    with pytest.raises(RuntimeError, match="not initialized"):
        await getattr(manager, method)(*args)
