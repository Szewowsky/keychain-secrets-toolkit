# Lookup Chain — How `get_secret.py` Finds Your Keys

`scripts/get_secret.py` walks through three sources, in order. It returns the first one that produces a value. Understanding this order matters when something doesn't work — you'll know exactly where to look.

## The chain

```
1. macOS Keychain (preferred)
   service = $KEYCHAIN_SERVICE (default: "my-secrets")
   account = KEY_NAME
   ↓ (no value)
2. Environment variable
   $KEY_NAME (but only if != "STORED_IN_KEYRING")
   ↓ (no value)
3. .env file
   line `KEY_NAME=value` (but only if value != "STORED_IN_KEYRING")
   ↓ (no value)
ERROR — key not found
```

## Step 1: Keychain

Two sub-paths, tried in order:

### 1a. `security` CLI

```bash
security find-generic-password -a KEY_NAME -s my-secrets -w
```

This is the canonical way and what `setup_keyring.py` and `add-generic-password` produce. Fast, scriptable, native.

### 1b. Python `keyring` library (fallback)

Some tools (older versions of Python's `keyring`, or `keyring.set_password()` called manually) write entries in a "blob" format that `security ... -w` returns empty for. The Python `keyring` library reads them correctly.

This fallback is automatic — you don't have to think about it. It's there to catch entries created by mixed tooling.

## Step 2: Environment variable

If the key isn't in Keychain, the script checks `os.environ[KEY_NAME]`. This lets CI systems, Docker containers, or one-off shells inject keys via env without needing Keychain access.

**Special case:** if the env var is set to literally `STORED_IN_KEYRING`, it's treated as "not found" — that's the placeholder convention. You can `source .env` to load all placeholders into the environment without breaking the lookup chain.

## Step 3: `.env` file

Last resort. Reads `.env` in the repo root, parses `KEY=value` lines. Skip:
- Empty lines
- Comments (`# ...`)
- Lines where `value == "STORED_IN_KEYRING"`

This is mostly for backward compatibility — if you haven't migrated to Keychain yet, the script still works. **After you migrate, `.env` only has placeholders, so this step always returns nothing.** That's the secure end state.

## The `KEYCHAIN_SERVICE` env var

By default, all keys live under the Keychain service name `my-secrets`. You can override this per-project:

```bash
# Shell:
KEYCHAIN_SERVICE=my-project python3 scripts/get_secret.py OPENAI_API_KEY

# Persistent for your shell session:
export KEYCHAIN_SERVICE=my-project

# In a wrapper script (.zshrc or per-project .envrc with direnv):
export KEYCHAIN_SERVICE="$(basename $(pwd))"
```

This lets you separate keys per project: `acme-prod-keys`, `personal-secrets`, `client-x-keys`, etc. All in the same macOS Keychain, separated by service name.

## Why no `.env` write-back

Some tools auto-write resolved keys back to `.env` for caching. **This toolkit deliberately does not.** Because:
- If `.env` ever held real values again, it'd risk re-leaking on next commit
- Keychain is already cache-fast (microseconds)
- The placeholder pattern makes accidental commits visible: a real value in `.env` after migration is a red flag

## Debugging: which path did `get_secret.py` take?

If a key returns the wrong value or `not found`, check sources in order:

```bash
# 1. Is it in Keychain?
security find-generic-password -a OPENAI_API_KEY -s my-secrets -w
# (you'll be prompted for your login password)

# 2. Is it in env?
echo "${OPENAI_API_KEY:-not-set}"

# 3. Is it in .env?
grep "^OPENAI_API_KEY=" .env
```

If `security find-generic-password` returns empty but Python `keyring` finds it, the entry is in blob format — that's the case the 1b fallback exists for.

## See also

- `docs/prefix-validation.md` — what happens if the value found is the wrong provider's key
- `docs/troubleshooting.md` — stale tokens, truncation, cross-provider mismatches
