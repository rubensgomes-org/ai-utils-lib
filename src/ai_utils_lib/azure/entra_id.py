"""Microsoft Entra ID token provider for AI Utilities."""

from collections.abc import Awaitable, Callable

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider

__all__ = ["AI_FOUNDRY_SCOPE", "COGNITIVE_SERVICES_SCOPE", "ai_token_provider"]

# Scope for Azure OpenAI and Foundry model inference
COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"

# Scope for Azure AI Foundry project and Agent APIs
AI_FOUNDRY_SCOPE = "https://ai.azure.com/.default"


def ai_token_provider(
    credential: AsyncTokenCredential,
    scope: str = COGNITIVE_SERVICES_SCOPE,
) -> Callable[[], Awaitable[str]]:
    """Return an async callable yielding a cached, auto-renewed token.

    Entra ID tokens expire, so a fixed token passed as an API key stops
    working. Clients such as ``openai.AsyncOpenAI`` also accept this
    callable and call it whenever they need a key.

    ``scope`` selects the token's resource, e.g. ``AI_FOUNDRY_SCOPE``
    for Azure AI Foundry project APIs.

    ``credential`` must stay open while the returned callable is in use.
    """
    return get_bearer_token_provider(credential, scope)
