#!/bin/bash
# Real-world example: wrapper for n8n-mcp.
# Sanitized — replace placeholder URL with your own n8n instance.
#
# Wire into .mcp.json:
#   {
#     "mcpServers": {
#       "n8n": {
#         "command": "/absolute/path/to/examples/mcp-n8n-wrapper.sh"
#       }
#     }
#   }
#
# Then: chmod 755 examples/mcp-n8n-wrapper.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Edit this to point to your n8n instance:
export N8N_API_URL="${N8N_API_URL:-https://your-n8n-instance.example.com}"

N8N_API_KEY="$(python3 "$REPO_ROOT/scripts/get_secret.py" N8N_API_KEY 2>/dev/null || true)"

if [ -z "${N8N_API_KEY:-}" ]; then
  SERVICE="${KEYCHAIN_SERVICE:-my-secrets}"
  echo "ERROR: N8N_API_KEY not found in Keychain (service=$SERVICE, account=N8N_API_KEY)" >&2
  echo "Add it: security add-generic-password -U -a N8N_API_KEY -s $SERVICE -w '<your-key>'" >&2
  exit 1
fi

export N8N_API_KEY

exec npx -y n8n-mcp "$@"
