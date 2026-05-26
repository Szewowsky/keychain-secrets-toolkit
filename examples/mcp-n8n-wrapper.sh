#!/bin/bash
# Prawdziwy przykład: wrapper dla n8n-mcp.
# Zanonimizowano — zamień przykładowy URL na własną instancję n8n.
#
# Podepnij w .mcp.json:
#   {
#     "mcpServers": {
#       "n8n": {
#         "command": "/absolute/path/to/examples/mcp-n8n-wrapper.sh"
#       }
#     }
#   }
#
# Następnie: chmod 755 examples/mcp-n8n-wrapper.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Edytuj to, aby wskazywało na twoją instancję n8n:
export N8N_API_URL="${N8N_API_URL:-https://your-n8n-instance.example.com}"

N8N_API_KEY="$(python3 "$REPO_ROOT/scripts/get_secret.py" N8N_API_KEY 2>/dev/null || true)"

if [ -z "${N8N_API_KEY:-}" ]; then
  SERVICE="${KEYCHAIN_SERVICE:-my-secrets}"
  echo "BŁĄD: Nie znaleziono N8N_API_KEY w Keychain (service=$SERVICE, account=N8N_API_KEY)" >&2
  echo "Dodaj go: security add-generic-password -U -a N8N_API_KEY -s $SERVICE -w '<your-key>'" >&2
  exit 1
fi

export N8N_API_KEY

exec npx -y n8n-mcp "$@"
