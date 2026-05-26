# MCP Wrapper Pattern — Keys for MCP Servers Without Plaintext

If you use Claude Code (or any MCP host) with custom MCP servers, you've probably hit this:

```json
// .mcp.json
{
  "mcpServers": {
    "n8n": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_KEY": "sk-XXX-PLAINTEXT-IN-COMMITTED-FILE"  // ← bad
      }
    }
  }
}
```

That `env` field is the canonical way to pass secrets to an MCP server, but it lands in `.mcp.json`. Many projects commit `.mcp.json` (it tells teammates which MCP servers to use). And now your API key is in git history.

## The wrapper pattern

Instead of `command + env`, use a tiny shell wrapper that:

1. Reads the key from Keychain via `get_secret.py`
2. Exports it as an env var
3. `exec`'s the actual MCP server

```bash
#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

N8N_API_KEY="$(python3 "$REPO_ROOT/scripts/get_secret.py" N8N_API_KEY)"
export N8N_API_KEY

exec npx -y n8n-mcp "$@"
```

Wire into `.mcp.json` as `command`:

```json
{
  "mcpServers": {
    "n8n": {
      "command": "/absolute/path/to/scripts/mcp-n8n-wrapper.sh"
    }
  }
}
```

Now `.mcp.json` is safe to commit — it has a path, not a secret.

## Template + example included

This repo ships:

- `scripts/mcp-wrapper-template.sh` — generic template with placeholders. Copy, rename, fill in `KEY_NAME` and `MCP_PACKAGE`.
- `examples/mcp-n8n-wrapper.sh` — real-world wrapper for `n8n-mcp` (sanitized).

```bash
cp scripts/mcp-wrapper-template.sh scripts/mcp-stripe-wrapper.sh
# edit KEY_NAME and MCP_PACKAGE, then:
chmod +x scripts/mcp-stripe-wrapper.sh
```

## Multiple env vars (e.g. KEY + URL)

If the MCP server needs more than one env var (API URL, region, etc.), add them in the wrapper before `exec`:

```bash
#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export STRIPE_API_KEY="$(python3 "$REPO_ROOT/scripts/get_secret.py" STRIPE_API_KEY)"
export STRIPE_API_URL="${STRIPE_API_URL:-https://api.stripe.com}"
export STRIPE_API_VERSION="2024-06-20"

exec npx -y stripe-mcp "$@"
```

API URLs and config strings are fine to keep in the wrapper itself — they're not secrets.

## Limitation: SSE-type MCP servers

The wrapper pattern works for `type: "command"` (stdio-based) MCP servers. It does **not** work for `type: "sse"` (server-sent events):

```json
{
  "mcpServers": {
    "remote-thing": {
      "type": "sse",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer sk-XXX"  // ← no wrapper can resolve this
      }
    }
  }
}
```

Claude Code loads the URL and headers directly — there's no process to wrap. Your options:

1. **Accept plaintext in `.mcp.json`** with `.mcp.json` in `.gitignore`. Project-local only. Risky if you forget to gitignore.
2. **Run a local proxy** that injects the header from Keychain. The MCP host sees `Authorization: Bearer none` go to `http://localhost:PORT/proxy`, proxy replaces with real key, forwards to remote.

For most use cases, option 1 is fine if `.mcp.json` is gitignored. Option 2 is overkill unless the team commits `.mcp.json` and uses SSE servers heavily.

## Why `exec` instead of just running?

```bash
# Bad — leaves shell process running, child is orphaned on signals
npx -y n8n-mcp "$@"

# Good — replaces shell process, signals (SIGTERM from MCP host) reach the MCP server cleanly
exec npx -y n8n-mcp "$@"
```

`exec` is the difference between "MCP host kills the wrapper but the server keeps running" and "MCP host kills the server like it should."

## Why `chmod 755` matters

Without execute permission, the MCP host gets `permission denied` and the server silently fails to start (sometimes with cryptic logs). Always:

```bash
chmod 755 scripts/mcp-*-wrapper.sh
```

The wrapper file itself is safe to commit (`chmod 755` is fine) — there's no secret in it, only a reference to `get_secret.py`.
