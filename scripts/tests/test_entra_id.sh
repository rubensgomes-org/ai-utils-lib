#!/usr/bin/env bash
# Gets an Entra ID token with ai_token_provider and prints it masked.
# Usage: test_entra_id.sh [scope]
set -euo pipefail

scope="${1:-https://cognitiveservices.azure.com/.default}"

echo "Scope: $scope"

cd "$(dirname "$0")/../.."
uv run python - "$scope" <<'EOF'
import asyncio
import sys

from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.entra_id import ai_token_provider


async def main(scope: str) -> None:
    async with DefaultAzureCredential() as credential:
        print("Getting a token with DefaultAzureCredential...")
        provider = ai_token_provider(credential, scope)
        token = await provider()
        print(f"Token = …{token[-4:]} ({len(token)} characters)")


asyncio.run(main(sys.argv[1]))
EOF
