# keychain-secrets-toolkit

macOS Keychain-based secrets management for AI API keys + Claude Code MCP servers.

A small toolkit (two Python scripts, a shell wrapper template, a few docs) that keeps your AI API keys out of `.env` files, shell history, screenshots, and AI chat transcripts. Keys live in the macOS Keychain. Your code retrieves them via a single command that never leaks the value.

> **macOS only.** This toolkit relies on the native `security` CLI and Keychain. Windows/Linux equivalents (Credential Manager, GNOME Keyring) work in theory through the Python `keyring` library, but the scripts haven't been adapted or tested there.

## Why

The default way developers store AI API keys — putting them in `.env`, then committing the file by mistake, or copying the value into a ChatGPT prompt for "debugging" — leaks more keys per week than every real hack combined. This toolkit:

- Stores keys in macOS Keychain (OS-level vault, unlocked by your login password / Touch ID)
- Replaces `.env` values with `STORED_IN_KEYRING` placeholders, so the file is safe to commit
- Provides a unified lookup script — your code never sees the raw key in source or shell history
- Catches **cross-provider mistakes** (a key looks like the wrong provider's, it fails fast with a fix instruction instead of a generic 401)
- Includes an MCP wrapper pattern for Claude Code / MCP server users who can't put plaintext keys in `.mcp.json`

## The one rule

> **Never paste an API key into an AI chat (ChatGPT, Claude Code, Cursor, Gemini, anything else).**

Pasting a key into an AI tool puts it in the model's session context, the provider's pipeline logs, and your conversation transcript. The damage is permanent — the only fix is rotation.

Read **[docs/security-first.md](docs/security-first.md)** before anything else. It's short and load-bearing.

## Setup (5 minutes)

### 1. Clone

```bash
git clone https://github.com/Szewowsky/keychain-secrets-toolkit.git
cd keychain-secrets-toolkit
pip3 install --user -r requirements.txt
```

(Or use a virtual env — see `docs/troubleshooting.md` if `pip3 install` fails.)

### 2. Add your keys (pick one method)

**Method A — Interactive (recommended). The key never enters shell history or any file:**

```bash
python3 scripts/setup_keyring.py --interactive
```

Prompts for each key listed in `.env.example`. Press Enter to skip ones you don't have.

**Method B — Native macOS CLI, one at a time:**

```bash
security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w 'sk-proj-XXX'
security add-generic-password -U -a ANTHROPIC_API_KEY -s my-secrets -w 'sk-ant-XXX'
```

The whole command (including the key) lands in `~/.zsh_history`. Either prefix the command with a leading space (if your shell has `HIST_IGNORE_SPACE`) or run `history -d $(history | tail -1 | awk '{print $1}')` after to remove the last entry.

**Method C — Migrate from existing `.env`:**

```bash
# 1. Copy .env.example, fill in real values
cp .env.example .env
# edit .env in your favorite editor

# 2. Migrate (asks for confirmation):
python3 scripts/setup_keyring.py

# .env is now overwritten with STORED_IN_KEYRING placeholders.
```

### 3. Use it

In shell scripts:

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $(python3 scripts/get_secret.py OPENAI_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'
```

The shell expands `$(...)` before `curl` runs — the key flows from `python3` straight into the HTTP header, never appearing on stdout.

In Python:

```python
import subprocess

def get_secret(key_name):
    return subprocess.run(
        ["python3", "scripts/get_secret.py", key_name],
        capture_output=True, text=True, check=True
    ).stdout

openai_key = get_secret("OPENAI_API_KEY")
```

See `examples/usage-curl.sh` and `examples/usage-python.py` for more.

## Cross-provider validation (the bug nobody catches the first time)

Imagine you accidentally store your OpenRouter key under the `OPENAI_API_KEY` label. You send it to OpenAI. OpenAI returns `401 Unauthorized`. You spend an hour debugging your code.

This toolkit catches it before the request leaves:

```bash
python3 scripts/get_secret.py OPENAI_API_KEY
# →
# ERROR: OPENAI_API_KEY in Keychain looks like a OpenRouter key (starts with 'sk-or-').
# Most likely OPENROUTER_API_KEY was stored under the OPENAI_API_KEY label by mistake.
# Fix:
#   1) Get the real OPENAI_API_KEY: sk-proj-XXXX (from https://platform.openai.com/api-keys)
#   2) Overwrite the wrong entry: ...
```

Works for OpenAI, Anthropic, OpenRouter, Google Gemini out of the box. Add more in `scripts/get_secret.py` → `PROVIDER_FORMAT`. See [docs/prefix-validation.md](docs/prefix-validation.md).

Disable for tests: `python3 scripts/get_secret.py XYZ --no-validate`.

## MCP wrapper pattern (for Claude Code / MCP users)

If you use Claude Code with MCP servers, you've hit this — `.mcp.json` either has plaintext keys in `env:` (bad — commits to git) or no keys at all (and the MCP server fails).

Use the wrapper script pattern instead. `scripts/mcp-wrapper-template.sh` is a generic template; copy and edit:

```bash
cp scripts/mcp-wrapper-template.sh scripts/mcp-myserver-wrapper.sh
# edit KEY_NAME and MCP_PACKAGE
chmod +x scripts/mcp-myserver-wrapper.sh
```

Then in `.mcp.json`:

```json
{
  "mcpServers": {
    "myserver": {
      "command": "/absolute/path/to/scripts/mcp-myserver-wrapper.sh"
    }
  }
}
```

The wrapper reads the key from Keychain at startup, exports it for the MCP process, and `exec`'s into it. `.mcp.json` is safe to commit — it only has a path.

Real example: `examples/mcp-n8n-wrapper.sh` (n8n-mcp wrapper). Limitations and SSE-type MCP servers covered in [docs/mcp-pattern.md](docs/mcp-pattern.md).

## Per-project services (optional)

By default, keys live under Keychain service name `my-secrets`. Override per-project:

```bash
# One-off:
KEYCHAIN_SERVICE=acme-prod python3 scripts/get_secret.py OPENAI_API_KEY

# Persistent (.zshrc or per-project .envrc with direnv):
export KEYCHAIN_SERVICE="$(basename $(pwd))"
```

Different services keep keys for different projects isolated. Same Keychain, different namespaces.

## Layout

```
keychain-secrets-toolkit/
├── README.md                          # you are here
├── LICENSE                            # MIT
├── .env.example                       # template (4 generic AI providers)
├── requirements.txt                   # keyring>=24.0
├── scripts/
│   ├── get_secret.py                  # main lookup (Keychain → env → .env) + per-provider validation
│   ├── setup_keyring.py               # bulk migration from .env, or --interactive mode
│   └── mcp-wrapper-template.sh        # generic MCP wrapper (copy, edit KEY_NAME + MCP_PACKAGE)
├── examples/
│   ├── usage-curl.sh                  # curl with shell substitution
│   ├── usage-python.py                # subprocess + Python SDK pattern
│   └── mcp-n8n-wrapper.sh             # real wrapper example (sanitized)
└── docs/
    ├── security-first.md              # READ FIRST — where keys must never go
    ├── lookup-chain.md                # how get_secret.py finds your keys
    ├── prefix-validation.md           # cross-provider mismatch protection
    ├── mcp-pattern.md                 # MCP wrappers + SSE limitations
    └── troubleshooting.md             # common errors and diagnostics
```

## What's not covered

- **Non-macOS platforms.** Python `keyring` works on Windows/Linux, but the `security` CLI calls don't. The scripts would need refactoring to use `keyring` exclusively. PRs welcome.
- **SSO / OAuth flows.** OAuth tokens expire — they're not API keys. Storing them under `_API_KEY` labels works for a while then fails. Don't.
- **Server-side / headless setups.** macOS Keychain requires an unlocked login session. For headless servers, use the cloud provider's secret manager (AWS Secrets Manager, GCP Secret Manager, Vault, etc.).
- **Team key sharing.** This toolkit is single-user. If multiple people need the same key, use a password manager with sharing (1Password, Bitwarden) or a team secrets service.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome — especially:

- Windows / Linux platform support (refactor to use `keyring` library exclusively)
- More provider prefixes in `PROVIDER_FORMAT`
- Real MCP wrapper examples for other servers

Don't include real API keys in PRs, screenshots, or examples. Use `sk-proj-EXAMPLE-XXX` style placeholders.
