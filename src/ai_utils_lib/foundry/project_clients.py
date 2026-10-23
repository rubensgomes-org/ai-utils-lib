"""MS Foundry AI Project Clients for AI Utilities"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI


@asynccontextmanager
async def get_ai_project_clients(
    endpoint: str,
) -> AsyncGenerator[tuple[AIProjectClient, AsyncOpenAI]]:
    """
    Yields open, authenticated clients and ensures they are safely
    closed when the consuming function exits its context loop.
    """
    async with (
        # Obtain Microsoft credential in the following order:
        # 1. Service Principal using AZURE_CLIENT_ID, AZURE_TENANT_ID,
        #     AZURE_CLIENT_SECRET
        # 2. Workload identity
        # 3. Managed-identity (system or UAMI user-assigned)
        # 4. Active CLI signed in account
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=endpoint, credential=credential
        ) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        yield project_client, openai_client
