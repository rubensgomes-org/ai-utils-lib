"""Azure App Configuration settings reader for AI Utilities."""

import asyncio
import logging

from azure.appconfiguration import ConfigurationSetting
from azure.appconfiguration.aio import AzureAppConfigurationClient
from azure.identity.aio import DefaultAzureCredential

__all__ = ["list_settings"]

logger = logging.getLogger(__name__)

# In Azure Container Apps, `appcs_endpoint` is usually the
# APP_CONFIG_ENDPOINT environment variable, and the app's managed identity
# needs the "App Configuration Data Reader" role.

# How do Azure Container Apps get permission to read the Key Vault secret?
#
# All Azure Container Apps provisioned by Rubens' Terraform azure-iac
# project is assigned a shared UAMI (User-Assigned Managed Identiry), also
# provisioned by the same project.  This UAMI is granted a RBAC role permission
# ("App Configuration Data Reader ") to read App Configuration store.

# Where the appcs_endpoint should come from?
#
# APP_CONFIG_ENDPOINT : environment variable set in every Azure Container App
# by Rubens' Terraform azure-iac project that contains the URI of the
# shared App Configuration store (e.g., https://appcs-rgomes-lab.azconfig.io)


async def list_settings(
    appcs_endpoint: str, key_filter: str, label_filter: str
) -> list[ConfigurationSetting]:
    """Return the store's settings matching the key and label filters."""
    # DefaultAzureCredential tries, in order:
    #   1. Environment variables (e.g., AZURE_CLIENT_ID, AZURE_TENANT_ID)
    #   2. Managed identity (e.g., the UAMI of an Azure Container App)
    #   3. Your Azure CLI login
    async with (
        DefaultAzureCredential() as credential,
        AzureAppConfigurationClient(appcs_endpoint, credential) as client,
    ):
        logger.debug(
            "Listing App Configuration settings with key_filter: %s, "
            "label_filter: %s",
            key_filter,
            label_filter,
        )
        settings = client.list_configuration_settings(
            key_filter=key_filter, label_filter=label_filter
        )
        matching_settings: list[ConfigurationSetting] = []
        async for setting in settings:
            matching_settings.append(setting)
        return matching_settings


if __name__ == "__main__":
    # TESTING ONLY!!!
    _APP_CONFIG_ENDPOINT = "https://appcs-rgomes-lab.azconfig.io"
    _KEY_FILTER = "ai-utils-lib/*"
    settings = asyncio.run(
        list_settings(_APP_CONFIG_ENDPOINT, _KEY_FILTER, "lab")
    )
    for setting in settings:
        print(f"{setting.key} = {setting.value}")
