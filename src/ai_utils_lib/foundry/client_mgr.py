"""MS Foundry AI Client Manager for AI Utilities."""

import json
import logging
from contextlib import AsyncExitStack
from typing import Any

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    AgentDetails,
    AgentVersionDetails,
    PromptAgentDefinition,
    Tool,
)
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI
from openai.types.conversations import ConversationItem, ConversationItemList
from openai.types.responses import Response, ResponseInputItemParam
from openai.types.responses.response_input_param import ResponseInputParam
from pydantic import HttpUrl

__all__ = ["AIClientManager"]

_NOT_INITIALIZED: str = "AIClientManager is not initialized; call initialize()."
_INDENT: int = 2
_MAX_RETRIES: int = 5

logger = logging.getLogger(__package__)


class AIClientManager:
    """
    Keeps Foundry project and OpenAI clients open for the application
    lifetime (e.g., between startup and shutdown hooks).

    Design pattern: resource lifecycle manager backed by an AsyncExitStack.
    """

    def __init__(self, project_endpoint: HttpUrl) -> None:
        self.project_endpoint: HttpUrl = project_endpoint
        self._exit_stack: AsyncExitStack | None = None
        self._project_client: AIProjectClient | None = None
        self._openai_client: AsyncOpenAI | None = None

    @property
    def project_client(self) -> AIProjectClient:
        if self._project_client is None:
            raise RuntimeError(_NOT_INITIALIZED)
        return self._project_client

    @property
    def openai_client(self) -> AsyncOpenAI:
        if self._openai_client is None:
            raise RuntimeError(_NOT_INITIALIZED)
        return self._openai_client

    async def initialize(self) -> None:
        """
        Open the clients during application startup. Clients already opened
        are closed if a later one fails to open.
        """
        if self._exit_stack is not None:
            raise RuntimeError("AIClientManager is already initialized.")

        async with AsyncExitStack() as stack:
            logger.debug("Authenticating with DefaultAzureCredential")
            credential = await stack.enter_async_context(
                DefaultAzureCredential()
            )
            logger.debug("Creating AIProjectClient")
            project_client = await stack.enter_async_context(
                AIProjectClient(
                    endpoint=str(self.project_endpoint), credential=credential
                )
            )
            logger.debug("Creating AsyncOpenAI")
            openai_client = await stack.enter_async_context(
                project_client.get_openai_client(max_retries=_MAX_RETRIES)
            )
            self._exit_stack = stack.pop_all()

        self._project_client = project_client
        self._openai_client = openai_client

    async def save_user_msg_to_conversation(
        self, conversation_id: str, user_msg: str
    ) -> ConversationItemList:
        """Add user_msg to the conversation."""
        return await self.save_items_to_conversation(
            conversation_id,
            [{"type": "message", "role": "user", "content": user_msg}],
        )

    async def save_items_to_conversation(
        self, conversation_id: str, items: list[ResponseInputItemParam]
    ) -> ConversationItemList:
        """Add items to the server-side conversation history."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Saving items to conversation id %s:\n%s",
                conversation_id,
                json.dumps(items, indent=_INDENT, default=str),
            )
        return await self.openai_client.conversations.items.create(
            conversation_id=conversation_id,
            items=items,
        )

    async def fetch_agent(self, server_agent_name: str) -> AgentDetails:
        """Fetch a server-side agent from the Foundry Agent Service."""
        logger.debug(
            "Fetching server-side agent details for %s", server_agent_name
        )
        agent_details: AgentDetails = await self.project_client.agents.get(
            agent_name=server_agent_name
        )
        if logger.isEnabledFor(logging.DEBUG):
            agent_json: dict[str, Any] = agent_details.as_dict()
            logger.debug(
                "agent_details: %s",
                json.dumps(agent_json, indent=_INDENT, default=str),
            )
        return agent_details

    async def fetch_conversation(
        self, conversation_id: str
    ) -> list[ConversationItem]:
        """Fetch all conversation items from the Foundry Agent Service."""
        logger.debug("Fetching items for conversation id %s", conversation_id)
        pages = self.openai_client.conversations.items.list(
            conversation_id=conversation_id
        )
        # "async for" fetches the next page from the server when needed.
        items: list[ConversationItem] = []
        async for item in pages:
            items.append(item)
        return items

    async def debuglog_conversation(self, conversation_id: str) -> None:
        """Log entire conversation in DEBUG logging level."""
        if not logger.isEnabledFor(logging.DEBUG):
            return
        conversation_items: list[ConversationItem] = (
            await self.fetch_conversation(conversation_id)
        )
        items_dump = [
            item.model_dump(mode="json") for item in conversation_items
        ]
        logger.debug(
            "conversation items:\n%s", json.dumps(items_dump, indent=_INDENT)
        )

    async def post_conversation_to_agent(
        self,
        conversation_id: str,
        server_agent_name: str,
        agent_input: str | ResponseInputParam = "",
    ) -> Response:
        """Send previously stored conversation to server-side agent."""
        logger.debug(
            "Posting conversation id %s to server-side agent %s",
            conversation_id,
            server_agent_name,
        )
        # "agent_reference" routes the request through the Agent Service
        # rather than a raw LLM completion. The service builds the model
        # prompt server-side from the agent's instructions, model, tools and
        # the stored conversation items; the caller never sees that prompt.
        return await self.openai_client.responses.create(
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": server_agent_name,
                    "type": "agent_reference",
                }
            },
            input=agent_input,
        )

    async def create_agent(
        self,
        agent_name: str,
        model: str,
        instructions: str,
        tools: list[Tool] | None = None,
    ) -> AgentVersionDetails:
        """
        Create a new version of a server-side agent, creating the agent
        if it does not exist.
        """
        logger.info("Creating agent version with name: %s", agent_name)
        return await self.project_client.agents.create_version(
            agent_name=agent_name,
            definition=PromptAgentDefinition(
                model=model,
                instructions=instructions,
                tools=tools,
            ),
        )

    async def delete_agent(self, agent_name: str) -> None:
        """Delete the whole agent, including all its versions."""
        logger.info("Deleting agent with name: %s", agent_name)
        await self.project_client.agents.delete(agent_name=agent_name)

    async def close(self) -> None:
        """Close the clients during application shutdown. Idempotent."""
        if self._exit_stack is None:
            return

        exit_stack, self._exit_stack = self._exit_stack, None
        self._project_client = None
        self._openai_client = None
        await exit_stack.aclose()
