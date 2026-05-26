# Security First — Where Keys Must Never Go

Read this **before** you copy any key anywhere. This is the most important page in this toolkit.

## The one rule

> **Keys live in macOS Keychain. They never enter anything else.**

Anything else means: AI chats, commit messages, shell history, screenshots, screencasts, Slack DMs, sticky notes on your monitor, plain `.env` files committed to git. All of it is a leak vector.

## Never paste keys into AI chats

Claude Code, ChatGPT, Cursor, Gemini, Copilot Chat, anything else — **never paste API keys into any of them.**

When you paste a key into an AI tool:

- It enters the **session context** the model sees. The model technically "knows" it for the rest of that session.
- It is processed through the **provider's pipeline** (Anthropic, OpenAI, etc.). Reputable providers state they don't train on this data, but the data is still seen by their inference systems and stored in logs for the retention window stated in their terms.
- It lives in your **conversation transcript**. If you ever export, share, or screenshot that conversation — the key leaks.
- A future bug in the AI tool (eval logging, support escalation, debug snapshot) could surface that transcript to humans on the provider's side.

If you ever paste a key by accident — **rotate it immediately** (revoke in the provider's UI, generate a new one). Don't try to delete the chat history and hope. Assume compromise.

## Never put keys in commit messages or commands

```bash
# WRONG — leaks to git history forever:
git commit -m "fix auth; using OPENAI_API_KEY=sk-proj-abc123..."

# WRONG — leaks to ~/.zsh_history:
OPENAI_API_KEY=sk-proj-abc123... node app.js
```

Both of these are recoverable. `git log --all -p` finds the first one even after force-push (the orphan commits stay reachable via reflog and packfiles). `~/.zsh_history` is plaintext.

## Adding keys safely — three ways

Pick the most secure one your situation allows.

### 1. Interactive Python (preferred — no shell history)

```bash
python3 -c "import keyring; keyring.set_password('my-secrets', 'OPENAI_API_KEY', input('Key: '))"
```

You type the key at the prompt. It never enters `~/.zsh_history`, never enters a file, goes straight from your fingers to the Keychain.

### 2. Native macOS `security` CLI

```bash
security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w 'sk-proj-XXX'
```

The key **is** in your shell history with this one — `~/.zsh_history` will record the whole command. If you must use this, prefix the command with a leading space (zsh's `HIST_IGNORE_SPACE` if you have it set) or clear history afterward:

```bash
history -d $(history | tail -1 | awk '{print $1}')
```

### 3. Bulk migration from `.env`

```bash
python3 scripts/setup_keyring.py
```

Reads your existing `.env`, moves values to Keychain, overwrites `.env` with `STORED_IN_KEYRING` placeholders. Use this **once** when migrating from an unsafe setup. Don't keep going back to `.env` after.

## Never store keys in screenshots or screencasts

If you record your terminal:

- Clear scrollback first: `clear && printf '\e[3J'`
- Don't run `env` or `printenv` while recording
- Don't expand `$(...)` substitutions on-camera — the output stays in scroll buffer

A common leak: showing `.zshrc` or running history during a tutorial.

## Never commit `.env`

```bash
# .gitignore must contain:
.env
.env.local
.env.*.local
*.key
*.pem
credentials.json
.mcp.json
```

Already in this repo's `.gitignore`. If you copy this toolkit into another project, **copy `.gitignore` too** or merge those lines into the existing one.

## If a key leaks anyway

1. **Rotate immediately.** Revoke in the provider's UI, generate a new key, add it to Keychain.
2. **Don't try to rewrite git history.** Force-pushing over a leaked commit doesn't help — caches, forks, and the GitHub event log keep copies. The key is compromised; the only fix is rotation.
3. **Check provider's audit log.** OpenAI, Anthropic, etc. all have usage dashboards. Look for activity from IPs that aren't yours.

## Why this matters more than you think

The default leak vector for AI API keys in 2026 is not someone hacking your machine. It's:

- A `.env` file you forgot was committed
- A screenshot in a public Slack channel
- A key pasted into ChatGPT for "debugging"
- A `git log` shared during code review

This toolkit exists because **convenient is the enemy of safe**. Keychain isn't the fastest setup. It's the one that doesn't leak.
