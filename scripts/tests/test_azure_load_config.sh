#!/usr/bin/env bash
# Loads config.yaml overlaid with App Configuration and prints it.
# Usage: test_azure_load_config.sh [config] [endpoint] [label_filter]
#        [key_vault_uri]
set -euo pipefail

config="${1:-src/ai_utils_lib/config.yaml}"
endpoint="${2:-https://appcs-rgomes-lab.azconfig.io}"
label_filter="${3:-lab}"
key_vault_uri="${4:-https://kv-rgomes-lab.vault.azure.net/}"

echo "Config: $config"
echo "Endpoint: $endpoint"
echo "Label filter: $label_filter"
echo "Key Vault URI: $key_vault_uri"

cd "$(dirname "$0")/../.."
KEY_VAULT_URI="$key_vault_uri" uv run python - \
  "$config" "$endpoint" "$label_filter" <<'EOF'
import os
import sys
from pathlib import Path

from ai_utils_lib.config.azure_load_config import load_config

print("Loading config.yaml overlaid with App Configuration...")
config = load_config(Path(sys.argv[1]), *sys.argv[2:4])
api_key_env = config.model.api_key_env
if config.model.api_key is None:
    api_key_source = "not resolved"
elif api_key_env and os.environ.get(api_key_env):
    api_key_source = f"environment variable {api_key_env}"
else:
    api_key_source = "Key Vault"
print(f"AppConfig = {config}")
print(f"API key source: {api_key_source}")
EOF
