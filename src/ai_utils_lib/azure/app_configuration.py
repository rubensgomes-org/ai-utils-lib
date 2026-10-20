"""Azure App Configuration settings reader for AI Utilities."""

import logging

from azure.appconfiguration import ConfigurationSetting
from azure.appconfiguration.aio import AzureAppConfigurationClient
from azure.core.credentials_async import AsyncTokenCredential

__all__ = ["list_settings"]

logger = logging.getLogger(__name__)

# Characters that make a label filter match more than one label.
MULTI_LABEL_CHARS = ("*", ",")

# In Azure Container Apps, `appcs_endpoint` is usually the
# APP_CONFIG_ENDPOINT environment variable, and the managed identity needs
# the "App Configuration Data Reader" role (see docs/ROLES.md).


async def list_settings(
    credential: AsyncTokenCredential,
    appcs_endpoint: str,
    key_filter: str,
    label_filter: str,
) -> list[ConfigurationSetting]:
    """Return the store's settings matching the key and label filters.

    In ``key_filter``, ``*`` is a trailing wildcard, ``,`` separates
    values, and ``\\`` escapes either. ``label_filter`` must name exactly
    one label, so each key is returned at most once; unlabeled settings
    are excluded.

    ``credential`` is owned, and closed, by the caller.

    Raises:
        ValueError: ``label_filter`` contains ``*`` or ``,``.
        ClientAuthenticationError: ``credential`` cannot get a token.
        HttpResponseError: The request failed otherwise, e.g. the
            identity lacks access to the store.
        ServiceRequestError: The store is unreachable, e.g. a DNS
            failure or a non-HTTPS ``appcs_endpoint``.
    """
    _reject_multi_label(label_filter)
    async with AzureAppConfigurationClient(
        appcs_endpoint, credential
    ) as client:
        logger.debug(
            "Listing App Configuration %s settings with key_filter: %s, "
            "label_filter: %s",
            appcs_endpoint,
            key_filter,
            label_filter,
        )
        settings = client.list_configuration_settings(
            key_filter=key_filter, label_filter=label_filter
        )
        # TODO: resolve Key Vault references, returned as
        # SecretReferenceConfigurationSetting whose value is the secret's
        # URI as JSON. The store does not hold any yet.
        matching_settings: list[ConfigurationSetting] = []
        async for setting in settings:
            matching_settings.append(setting)
        return matching_settings


def _reject_multi_label(label_filter: str) -> None:
    """Raise ``ValueError`` if ``label_filter`` can match many labels."""
    if any(char in label_filter for char in MULTI_LABEL_CHARS):
        error_msg: str = (
            f"App Configuration label_filter {label_filter!r} must name "
            f"exactly one label, without {' or '.join(MULTI_LABEL_CHARS)}."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
