"""Microsoft Entra ID token provider for AI Utilities."""

import asyncio
from collections.abc import Awaitable, Callable

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider

__all__ = ["token_provider"]

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


# Entra ID tokens expire, so a fixed token passed as an API key stops
# working. Clients such as openai.AsyncOpenAI also accept a
# Callable[[], Awaitable[str]] and call it whenever they need a key;
# the provider returns a cached token and renews it before it expires.
# This is the reason for the token_provider function below.


def token_provider(
    credential: AsyncTokenCredential,
) -> Callable[[], Awaitable[str]]:
    """Return an async callable yielding a cached, auto-renewed token.

    ``credential`` must stay open while the returned callable is in use.
    """
    return get_bearer_token_provider(credential, COGNITIVE_SERVICES_SCOPE)


if __name__ == "__main__":
    # TESTING ONLY!!!
    _VISIBLE_CHARS = 4

    async def _main() -> None:
        async with DefaultAzureCredential() as credential:
            provider = token_provider(credential)
            token = await provider()
            print(
                f"Token = {token[:_VISIBLE_CHARS]}…{token[-_VISIBLE_CHARS:]}"
                f" ({len(token)} characters)"
            )
            print(
                f"Second call reuses cached token: {await provider() == token}"
            )

    asyncio.run(_main())
