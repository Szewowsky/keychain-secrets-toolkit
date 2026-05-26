#!/bin/bash
# Szablon ogólnego wrappera serwera MCP.
# Skopiuj ten plik, zmień nazwę na mcp-<server-name>-wrapper.sh, wypełnij zmienne.
#
# Cel: uniknięcie kluczy API w postaci zwykłego tekstu w .mcp.json.
# Zamiast tego, ten wrapper odczytuje klucz z macOS Keychain podczas uruchamiania i
# uruchamia serwer MCP (exec) z kluczem w zmiennych środowiskowych.
#
# Podłącz to w .mcp.json w ten sposób:
#   {
#     "mcpServers": {
#       "your-server": {
#         "command": "/absolute/path/to/scripts/mcp-your-server-wrapper.sh"
#       }
#     }
#   }
#
# Następnie nadaj uprawnienia wykonywania: chmod 755 mcp-your-server-wrapper.sh
#
# Ograniczenie: ten wzorzec NIE działa dla serwerów MCP typu "sse" —
# Claude Code ładuje URL i nagłówki bezpośrednio, więc klucz musi być już
# rozwiązany. Dla serwerów SSE zaakceptuj zwykły tekst w .mcp.json (z
# .mcp.json w .gitignore) lub użyj dedykowanego proxy.

set -euo pipefail

# --- KONFIGURACJA: edytuj poniższe ---
KEY_NAME="<YOUR_API_KEY_ENV_VAR>"                 # np. "OPENAI_API_KEY"
MCP_PACKAGE="<your-mcp-package>"                  # np. "n8n-mcp" lub "@some/mcp-server"
# Opcjonalnie: dodatkowe zmienne środowiskowe dla serwera MCP (odkomentuj i edytuj)
# export SOME_API_URL="${SOME_API_URL:-https://api.example.com}"
# --- KONIEC KONFIGURACJI ---

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VALUE="$(python3 "$REPO_ROOT/scripts/get_secret.py" "$KEY_NAME" 2>/dev/null || true)"

if [ -z "${VALUE:-}" ]; then
  SERVICE="${KEYCHAIN_SERVICE:-my-secrets}"
  echo "BŁĄD: nie znaleziono $KEY_NAME w Keychain (service=$SERVICE)" >&2
  echo "Dodaj go: security add-generic-password -U -a $KEY_NAME -s $SERVICE -w '<your-key>'" >&2
  exit 1
fi

# Wyeksportuj, aby proces serwera MCP to odziedziczył
export "$KEY_NAME=$VALUE"

# Przekaż do serwera MCP
exec npx -y "$MCP_PACKAGE" "$@"
