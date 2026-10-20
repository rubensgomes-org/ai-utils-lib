#!/usr/bin/env bash
# Lists App Configuration settings with list_settings.
# Usage: test_app_configuration.sh [endpoint] [key_filter] [label_filter]
set -euo pipefail

cd "$(dirname "$0")/../.."
uv run python - \
  "${1:-https://appcs-rgomes-lab.azconfig.io}" \
  "${2:-ai-utils*}" \
  "${3:-lab}" <<'EOF'
import asyncio
import sys

from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.app_configuration import list_settings


async def main(endpoint: str, key_filter: str, label_filter: str) -> list:
    async with DefaultAzureCredential() as credential:
        return await list_settings(
            credential, endpoint, key_filter, label_filter
        )


for setting in asyncio.run(main(*sys.argv[1:4])):
    print(f"{setting.key} = {setting.value}")
EOF
