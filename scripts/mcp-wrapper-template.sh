#!/bin/bash
# Generic MCP server wrapper template.
# Copy this file, rename to mcp-<server-name>-wrapper.sh, fill in placeholders.
#
# Purpose: avoid plaintext API keys in .mcp.json.
# Instead, this wrapper reads the key from macOS Keychain at startup and
# exec's the MCP server with the key in environment.
#
# Wire it into .mcp.json like this:
#   {
#     "mcpServers": {
#       "your-server": {
#         "command": "/absolute/path/to/scripts/mcp-your-server-wrapper.sh"
#       }
#     }
#   }
#
# Then chmod +x this file: chmod 755 mcp-your-server-wrapper.sh
#
# Limitation: this pattern does NOT work for MCP servers of type "sse" —
# Claude Code loads the URL + headers directly, so the key must already be
# resolved. For SSE servers, either accept plaintext in .mcp.json (with
# .mcp.json in .gitignore) or use a dedicated proxy.

set -euo pipefail

# --- CONFIG: edit these ---
KEY_NAME="<YOUR_API_KEY_ENV_VAR>"                 # e.g. "OPENAI_API_KEY"
MCP_PACKAGE="<your-mcp-package>"                  # e.g. "n8n-mcp" or "@some/mcp-server"
# Optional: extra env vars for the MCP server (uncomment and edit)
# export SOME_API_URL="${SOME_API_URL:-https://api.example.com}"
# --- END CONFIG ---

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VALUE="$(python3 "$REPO_ROOT/scripts/get_secret.py" "$KEY_NAME" 2>/dev/null || true)"

if [ -z "${VALUE:-}" ]; then
  SERVICE="${KEYCHAIN_SERVICE:-my-secrets}"
  echo "ERROR: $KEY_NAME not found in Keychain (service=$SERVICE)" >&2
  echo "Add it: security add-generic-password -U -a $KEY_NAME -s $SERVICE -w '<your-key>'" >&2
  exit 1
fi

# Export so the MCP server process inherits it
export "$KEY_NAME=$VALUE"

# Hand off to the MCP server
exec npx -y "$MCP_PACKAGE" "$@"
