#!/usr/bin/env bash
# Lists App Configuration settings with list_settings.
# Usage: test_app_configuration.sh [endpoint] [key_filter] [label_filter]
set -euo pipefail

endpoint="${1:-https://appcs-rgomes-lab.azconfig.io}"
key_filter="${2:-ai-utils-lib/*}"
label_filter="${3:-lab}"

echo "Endpoint: $endpoint"
echo "Key filter: $key_filter"
echo "Label filter: $label_filter"

cd "$(dirname "$0")/../.."
uv run python - "$endpoint" "$key_filter" "$label_filter" <<'EOF'
import asyncio
import sys

from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.app_configuration import list_settings


async def main(endpoint: str, key_filter: str, label_filter: str) -> list:
    async with DefaultAzureCredential() as credential:
        print("Listing settings with DefaultAzureCredential...")
        return await list_settings(
            credential, endpoint, key_filter, label_filter
        )


settings = asyncio.run(main(*sys.argv[1:4]))
print(f"Found {len(settings)} settings:")
for setting in settings:
    print(f"{setting.key} = {setting.value}")
EOF
