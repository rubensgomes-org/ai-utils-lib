#!/usr/bin/env bash
# Reads a Key Vault secret with read_secret and prints it masked.
# Usage: test_key_vault.sh [vault_url] [secret_name]
set -euo pipefail

vault_url="${1:-https://kv-rgomes-lab.vault.azure.net/}"
secret_name="${2:-ca-mathagent--NVIDIA-API-KEY}"

echo "Vault URL: $vault_url"
echo "Secret name: $secret_name"

cd "$(dirname "$0")/../.."
uv run python - "$vault_url" "$secret_name" <<'EOF'
import asyncio
import sys

from azure.identity.aio import DefaultAzureCredential

from ai_utils_lib.azure.key_vault import read_secret


async def main(vault_url: str, name: str) -> str:
    async with DefaultAzureCredential() as credential:
        print("Reading secret with DefaultAzureCredential...")
        return await read_secret(credential, vault_url, name)


value = asyncio.run(main(sys.argv[1], sys.argv[2]))
masked = f"…{value[-4:]}" if len(value) > 12 else "…"
print(f"{sys.argv[2]} = {masked} ({len(value)} characters)")
EOF
