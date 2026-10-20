"""Azure Key Vault reader for AI Utilities."""

import logging
import re

from azure.core.credentials_async import AsyncTokenCredential
from azure.keyvault.secrets.aio import SecretClient

__all__ = ["read_secret"]

logger = logging.getLogger(__name__)

SECRET_NAME_PATTERN = re.compile(r"[0-9a-zA-Z-]{1,127}")

# In Azure Container Apps, `vault_url` is usually the KEY_VAULT_URI
# environment variable, and the managed identity needs the
# "Key Vault Secrets User" role (see docs/ROLES.md).


async def read_secret(
    credential: AsyncTokenCredential, vault_url: str, secret_name: str
) -> str:
    """Return the value of secret ``secret_name`` in ``vault_url``.

    Surrounding whitespace, such as a trailing newline, is stripped.
    ``credential`` is owned, and closed, by the caller.

    Raises:
        ValueError: ``secret_name`` is not 1-127 alphanumerics or dashes,
            or the secret value is empty or blank.
        ResourceNotFoundError: The secret does not exist.
        ClientAuthenticationError: ``credential`` cannot get a token.
        HttpResponseError: The request failed otherwise, e.g. the
            identity lacks access or the secret is disabled.
    """
    _validate_secret_name(secret_name)
    async with SecretClient(
        vault_url=vault_url, credential=credential
    ) as client:
        logger.debug(
            "Reading secret: %s from Key Vault: %s", secret_name, vault_url
        )
        secret = await client.get_secret(secret_name)
        value: str = (secret.value or "").strip()
        if not value:
            error_msg: str = (
                f"Key Vault secret {secret_name} in {vault_url} is empty "
                "or blank."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        return value


def _validate_secret_name(secret_name: str) -> None:
    """Raise ``ValueError`` if Key Vault would reject ``secret_name``."""
    if not SECRET_NAME_PATTERN.fullmatch(secret_name):
        error_msg: str = (
            f"Key Vault secret name {secret_name!r} must be 1-127 "
            "alphanumerics or dashes."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
