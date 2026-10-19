"""Azure Key Vault reader for AI Utilities."""

import asyncio
import logging

from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

__all__ = ["read_secret"]

logger = logging.getLogger(__name__)

# In Azure Container Apps, `vault_url` is usually the KEY_VAULT_URI
# environment variable, and the app's managed identity needs the
# "Key Vault Secrets User" role.

# How do Azure Container Apps get permission to read the Key Vault secret?
#
# All Azure Container Apps provisioned by Rubens' Terraform azure-iac
# project is assigned a shared UAMI (User-Assigned Managed Identiry),
# also provisioned by the same project.  This UAMI is granted a RBAC role
# permission ("Key Vault Secrets User") to read Key Vault secrets.

# Where the vaulr_url should come from?
#
# KEY_VAULT_URI : environment variable set in every Azure Container App
# by Rubens' Terraform azure-iac project that contains the URI of the
# shared Key Vault store (e.g., https://kv-rgomes-lab.vault.azure.net/)


async def read_secret(vault_url: str, secret_name: str) -> str:
    """Return the non-empty value of secret ``secret_name`` in ``vault_url``."""
    # DefaultAzureCredential tries, in order:
    #   1. Environment variables (e.g., AZURE_CLIENT_ID, AZURE_TENANT_ID)
    #   2. Managed identity (e.g., the UAMI of an Azure Container App)
    #   3. Your Azure CLI login
    async with (
        DefaultAzureCredential() as credential,
        SecretClient(vault_url=vault_url, credential=credential) as client,
    ):
        logger.debug(
            "Reading secret: %s from Key Vault: %s", secret_name, vault_url
        )
        secret = await client.get_secret(secret_name)
        if not secret.value:
            raise ValueError(
                f"Key Vault secret {secret_name} in {vault_url} is empty."
            )
        return secret.value


if __name__ == "__main__":
    # TESTING ONLY!!!
    _KEY_VAULT_URI = "https://kv-rgomes-lab.vault.azure.net/"
    _SECRET_NAME = "ca-mathagent--FOUNDRY-API-KEY"
    _VISIBLE_CHARS = 4
    secret_value = asyncio.run(read_secret(_KEY_VAULT_URI, _SECRET_NAME))
    print(
        f"{_SECRET_NAME} = {secret_value[:_VISIBLE_CHARS]}…"
        f"{secret_value[-_VISIBLE_CHARS:]} ({len(secret_value)} characters)"
    )
