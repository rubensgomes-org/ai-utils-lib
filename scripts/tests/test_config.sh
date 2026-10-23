#!/usr/bin/env bash
# Loads config.yaml with load_config and aload_config of ai_utils_lib.config.
# Usage: test_config.sh [config] [endpoint] [app_env] [key_vault_uri]
# An empty endpoint ("") loads config.yaml only.
set -euo pipefail

config="${1:-src/ai_utils_lib/config.yaml}"
endpoint="${2-https://appcs-rgomes-lab.azconfig.io}"
app_env="${3:-lab}"
key_vault_uri="${4:-https://kv-rgomes-lab.vault.azure.net/}"

echo "Config: $config"
echo "Endpoint: ${endpoint:-(none, config.yaml only)}"
if [[ -n "$endpoint" ]]; then
  echo "APP_ENV: $app_env"
  echo "Key Vault URI: $key_vault_uri"
fi

cd "$(dirname "$0")/../.."
APP_CONFIG_ENDPOINT="$endpoint" APP_ENV="$app_env" \
  KEY_VAULT_URI="$key_vault_uri" uv run python - "$config" <<'EOF'
import asyncio
import os
import sys
from pathlib import Path

from ai_utils_lib.config import aload_config, load_config

print("Loading config with load_config...")
config = load_config(Path(sys.argv[1]))
api_key_env = config.model.api_key_env
if config.model.api_key is None:
    api_key_source = "not resolved"
elif api_key_env and os.environ.get(api_key_env):
    api_key_source = f"environment variable {api_key_env}"
else:
    api_key_source = "Key Vault"
print(f"AppConfig = {config}")
print(f"API key source: {api_key_source}")
print("Loading config with aload_config...")
async_config = asyncio.run(aload_config(Path(sys.argv[1])))
print(f"aload_config matches: {async_config == config}")
EOF
