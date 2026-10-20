#!/usr/bin/env bash
# Loads config.yaml overlaid with App Configuration and prints it.
# Usage: test_azure_config.sh [package] [endpoint] [label_filter]
set -euo pipefail

cd "$(dirname "$0")/../.."
uv run python - \
  "${1:-ai_utils_lib.config}" \
  "${2:-https://appcs-rgomes-lab.azconfig.io}" \
  "${3:-lab}" <<'EOF'
import sys

from ai_utils_lib.azure.config import load_config

print(f"AppConfig = {load_config(*sys.argv[1:4])}")
EOF
