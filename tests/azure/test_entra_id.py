"""Tests for ai_utils_lib.azure.entra_id."""

import time
from typing import Any, Self

from azure.core.credentials import AccessToken

from ai_utils_lib.azure.entra_id import (
    AI_FOUNDRY_SCOPE,
    COGNITIVE_SERVICES_SCOPE,
    ai_token_provider,
)

TOKEN = "test-bearer-token"
TOKEN_LIFETIME_SECONDS = 3600


class FakeCredential:
    """An async credential that records its token requests."""

    def __init__(self) -> None:
        self.requested_scopes: list[tuple[str, ...]] = []
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()

    async def get_token(self, *scopes: str, **_kwargs: Any) -> AccessToken:
        self.requested_scopes.append(scopes)
        return AccessToken(TOKEN, int(time.time()) + TOKEN_LIFETIME_SECONDS)

    async def close(self) -> None:
        self.closed = True


async def test_ai_token_provider_returns_credential_token() -> None:
    provider = ai_token_provider(FakeCredential())

    assert await provider() == TOKEN


async def test_ai_token_provider_requests_cognitive_services_scope() -> None:
    credential = FakeCredential()

    await ai_token_provider(credential)()

    assert credential.requested_scopes == [(COGNITIVE_SERVICES_SCOPE,)]


async def test_ai_token_provider_requests_given_scope() -> None:
    credential = FakeCredential()

    await ai_token_provider(credential, AI_FOUNDRY_SCOPE)()

    assert credential.requested_scopes == [(AI_FOUNDRY_SCOPE,)]


async def test_ai_token_provider_reuses_unexpired_token() -> None:
    credential = FakeCredential()
    provider = ai_token_provider(credential)

    await provider()
    await provider()

    assert len(credential.requested_scopes) == 1


async def test_ai_token_provider_leaves_credential_open() -> None:
    credential = FakeCredential()

    await ai_token_provider(credential)()

    assert credential.closed is False
