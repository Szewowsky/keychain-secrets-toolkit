# Troubleshooting

Common issues and how to diagnose them.

## `Secret 'XYZ' not found in Keychain, env, or .env`

Order of likely causes (most common first):

1. **Wrong service name.** The toolkit defaults to service `my-secrets`. If you stored the key under a different service, set the env var:
   ```bash
   KEYCHAIN_SERVICE=your-service-name python3 scripts/get_secret.py XYZ
   ```

2. **Key is under `label` instead of `account`.** Older conventions used `-l KEY_NAME` (label) instead of `-a KEY_NAME` (account). The new toolkit uses `account=KEY_NAME`. To migrate:
   ```bash
   # Read from old location (with label):
   security find-generic-password -a robert -s my-secrets -l XYZ -w

   # Write to new location (with account):
   security add-generic-password -U -a XYZ -s my-secrets -w '<value>'
   ```

3. **You added the key but it doesn't show up.** Verify:
   ```bash
   security find-generic-password -a XYZ -s my-secrets -w
   ```
   If this returns empty but you can find it in Keychain Access app, you might have written it via `keyring.set_password()` (blob format). The Python fallback in `get_secret.py` will read it, but the `security` CLI alone won't.

## `ERROR: XYZ has an unknown format`

The value in Keychain doesn't start with any of the expected prefixes for that provider. Causes:

- You stored the **wrong provider's key** under that label. See [prefix-validation.md](prefix-validation.md) — the error message will suggest which label to use instead.
- The key is **truncated**. Run:
  ```bash
  python3 scripts/get_secret.py XYZ --no-validate | wc -c
  ```
  Most AI API keys are 50-200 characters. If you see <20, it's truncated.
- The key was **stored with quotes**. Some shells preserve quotes inside `-w '...'`. Re-store without:
  ```bash
  # Wrong (quotes literal):
  security add-generic-password -U -a XYZ -s my-secrets -w "'sk-proj-XXX'"

  # Correct (single quotes consumed by shell):
  security add-generic-password -U -a XYZ -s my-secrets -w 'sk-proj-XXX'
  ```

## `401 Unauthorized` from the API even though the key is in Keychain

Diagnostic order:

1. **Is `--no-validate` needed?** If yes, you're using a custom-prefix key that the toolkit doesn't know about. Skip to step 3.
2. **Did `get_secret.py` actually return what you expect?** Print the first 12 chars (safe — that's just the prefix):
   ```bash
   python3 scripts/get_secret.py XYZ | head -c 12
   ```
   Compare to the prefix you'd expect.
3. **Is the key revoked?** Check the provider's dashboard. Keys are often invalidated when you rotate but you forget which one was new.
4. **Is the key for the right account/workspace?** Some providers (OpenAI, Anthropic) have project-scoped keys. A project key for project A returns `401` for project B requests.
5. **OAuth tokens vs API keys.** Tokens like `ya29.a0Aa...` (Google) or `gho_...` (GitHub) **expire**. They're not API keys. If you stored an OAuth token under an `_API_KEY` label, it'll work for a while then fail at the expiration time. Replace with a real API key (or persist the OAuth refresh flow).

## Keychain prompts for password every time

Keychain Access by default unlocks on login. If it's prompting per-command:

1. Open **Keychain Access** app
2. Right-click the entry → **Get Info** → **Access Control** tab
3. Add `/usr/bin/security` and `/usr/bin/python3` to **Always allow access by these applications**

For maximum convenience: set "Allow all applications" — but only for development machines, not shared/work machines.

## `pip install keyring` fails with `externally-managed-environment`

macOS Python 3.12+ enforces PEP 668. Options:

```bash
# Option 1 — user install (recommended for personal tools):
pip3 install --user keyring

# Option 2 — virtual env (recommended for projects):
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Option 3 — Homebrew Python (drops PEP 668 enforcement):
brew install python && pip3 install keyring

# Option 4 — only if you accept the risk:
pip3 install --break-system-packages keyring
```

Most users want option 1 or 2.

## Wrapper script fails: "command not found" or "permission denied"

```bash
chmod 755 scripts/mcp-*-wrapper.sh
```

Also check the **first line** of the wrapper (`#!/bin/bash`) — if it has Windows line endings (`\r\n`), bash can't parse it. Fix:

```bash
sed -i '' 's/\r$//' scripts/mcp-*-wrapper.sh
```

## I accidentally pasted a key into an AI chat / committed it

See **[security-first.md](security-first.md)** — "If a key leaks anyway".

TL;DR: rotate immediately in the provider's dashboard. Don't try to clean git history — caches and forks keep the old commits reachable. The key is compromised the moment it leaves your terminal; the only fix is rotation.

## Adding diagnostic logging

If `get_secret.py` mysteriously returns wrong values or nothing, add temporary debug logging:

```python
# Top of get_secret.py:
import sys
DEBUG = True

# Inside get_from_keychain:
if DEBUG:
    print(f"[debug] trying security CLI: account={key_name} service={service}", file=sys.stderr)
```

This logs to stderr so it doesn't pollute the stdout value (the key itself). Remove when done.
