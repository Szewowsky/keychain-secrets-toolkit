# Wzorzec MCP Wrapper — Klucze dla serwerów MCP bez plaintextu

Jeśli używasz Claude Code (lub dowolnego hosta MCP) z własnymi serwerami MCP, prawdopodobnie spotkałeś się z tym problemem:

```json
// .mcp.json
{
  "mcpServers": {
    "n8n": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_KEY": "sk-XXX-PLAINTEXT-IN-COMMITTED-FILE"  // ← źle
      }
    }
  }
}
```

Pole `env` to kanoniczny sposób przekazywania sekretów do serwera MCP, ale ląduje ono w `.mcp.json`. Wiele projektów commituje plik `.mcp.json` (informuje on zespół, jakich serwerów MCP używać). I w ten sposób Twój klucz API trafia do historii git.

## Wzorzec wrappera

Zamiast `command + env`, użyj małego wrappera w shellu, który:

1. Odczytuje klucz z Keychain za pomocą `get_secret.py`
2. Eksportuje go jako zmienną środowiskową
3. Uruchamia właściwy serwer MCP za pomocą `exec`

```bash
#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

N8N_API_KEY="$(python3 "$REPO_ROOT/scripts/get_secret.py" N8N_API_KEY)"
export N8N_API_KEY

exec npx -y n8n-mcp "$@"
```

Podepnij to w `.mcp.json` jako `command`:

```json
{
  "mcpServers": {
    "n8n": {
      "command": "/absolute/path/to/scripts/mcp-n8n-wrapper.sh"
    }
  }
}
```

Teraz plik `.mcp.json` można bezpiecznie commitować — zawiera ścieżkę, a nie sekret.

## Szablon + przykład w zestawie

To repozytorium zawiera:

- `scripts/mcp-wrapper-template.sh` — generyczny szablon z placeholderami. Skopiuj, zmień nazwę, wypełnij `KEY_NAME` i `MCP_PACKAGE`.
- `examples/mcp-n8n-wrapper.sh` — rzeczywisty wrapper dla `n8n-mcp` (zanonimizowany).

```bash
cp scripts/mcp-wrapper-template.sh scripts/mcp-stripe-wrapper.sh
# edytuj KEY_NAME i MCP_PACKAGE, a następnie:
chmod +x scripts/mcp-stripe-wrapper.sh
```

## Wiele zmiennych środowiskowych (np. KEY + URL)

Jeśli serwer MCP potrzebuje więcej niż jednej zmiennej środowiskowej (API URL, region itp.), dodaj je we wrapperze przed `exec`:

```bash
#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export STRIPE_API_KEY="$(python3 "$REPO_ROOT/scripts/get_secret.py" STRIPE_API_KEY)"
export STRIPE_API_URL="${STRIPE_API_URL:-https://api.stripe.com}"
export STRIPE_API_VERSION="2024-06-20"

exec npx -y stripe-mcp "$@"
```

Adresy API URL i ciągi konfiguracyjne można bez problemu trzymać w samym wrapperze — nie są to sekrety.

## Ograniczenie: Serwery MCP typu SSE

Wzorzec wrappera działa dla serwerów MCP `type: "command"` (opartych na stdio). **Nie** działa dla `type: "sse"` (server-sent events):

```json
{
  "mcpServers": {
    "remote-thing": {
      "type": "sse",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer sk-XXX"  // ← żaden wrapper tego nie rozwiąże
      }
    }
  }
}
```

Claude Code ładuje URL i nagłówki bezpośrednio — nie ma procesu, który można by owrapować. Twoje opcje to:

1. **Zaakceptowanie plaintextu w `.mcp.json`** z dodaniem `.mcp.json` do `.gitignore`. Tylko lokalnie dla projektu. Ryzykowne, jeśli zapomnisz dodać do gitignore.
2. **Uruchomienie lokalnego proxy**, które wstrzykuje nagłówek z Keychain. Host MCP wysyła `Authorization: Bearer none` do `http://localhost:PORT/proxy`, proxy podmienia go na prawdziwy klucz i przekazuje do zdalnego serwera.

W większości przypadków opcja 1 jest w porządku, jeśli `.mcp.json` jest w gitignore. Opcja 2 to overkill, chyba że zespół commituje `.mcp.json` i intensywnie korzysta z serwerów SSE.

## Dlaczego `exec` zamiast po prostu uruchomić?

```bash
# Źle — proces shella zostaje, proces potomny osierocony przy sygnałach
npx -y n8n-mcp "$@"

# Dobrze — zastępuje proces shella, sygnały (SIGTERM z hosta MCP) czysto docierają do serwera MCP
exec npx -y n8n-mcp "$@"
```

`exec` to różnica między "host MCP zabija wrappera, ale serwer nadal działa" a "host MCP zabija serwer tak, jak powinien".

## Dlaczego `chmod 755` ma znaczenie

Bez uprawnień do wykonywania, host MCP otrzymuje `permission denied` i serwer po cichu nie uruchamia się (czasami z zagadkowymi logami). Zawsze rób:

```bash
chmod 755 scripts/mcp-*-wrapper.sh
```

Sam plik wrappera można bezpiecznie commitować (`chmod 755` jest w porządku) — nie ma w nim żadnego sekretu, tylko odwołanie do `get_secret.py`.
