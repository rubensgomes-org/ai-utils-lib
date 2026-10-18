"""Microsoft Entra ID token provider for AI Utilities."""

from collections.abc import Awaitable, Callable

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


def token_provider(
    credential: DefaultAzureCredential,
) -> Callable[[], Awaitable[str]]:
    """Return an async callable yielding a cached, auto-renewed token."""
    return get_bearer_token_provider(credential, COGNITIVE_SERVICES_SCOPE)
