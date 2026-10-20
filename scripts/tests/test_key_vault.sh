#!/usr/bin/env bash
# Reads a Key Vault secret with read_secret and prints it masked.
# Usage: test_key_vault.sh [vault_url] [secret_name]
set -euo pipefail

cd "$(dirname "$0")/../.."
uv run python - \
  "${1:-https://kv-rgomes-lab.vault.azure.net/}" \
  "${2:-ca-mathagent--FOUNDRY-API-KEY}" <<'EOF'
import asyncio
import sys

from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.key_vault import read_secret


async def main(vault_url: str, name: str) -> str:
    async with DefaultAzureCredential() as credential:
        return await read_secret(credential, vault_url, name)


value = asyncio.run(main(sys.argv[1], sys.argv[2]))
print(f"{sys.argv[2]} = {value[:4]}…{value[-4:]} ({len(value)} characters)")
EOF
