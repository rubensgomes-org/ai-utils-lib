#!/usr/bin/env bash
# Gets an Entra ID token with ai_token_provider and prints it masked.
# Usage: test_entra_id.sh
set -euo pipefail

cd "$(dirname "$0")/../.."
uv run python - <<'EOF'
import asyncio

from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.entra_id import ai_token_provider


async def main() -> None:
    async with DefaultAzureCredential() as credential:
        provider = ai_token_provider(credential)
        token = await provider()
        print(f"Token = {token[:4]}…{token[-4:]} ({len(token)} characters)")
        print(f"Second call reuses cached token: {await provider() == token}")


asyncio.run(main())
EOF
