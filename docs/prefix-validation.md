# Prefix Validation — Catching Cross-Provider Mismatches

A weird real-world bug: you ask for `OPENAI_API_KEY`, get a value back, send it to OpenAI, and the API returns a generic `401 Unauthorized`. After an hour of debugging your code, you realize the value stored under `OPENAI_API_KEY` was actually your **OpenRouter** key, mislabeled.

This is the bug prefix validation catches. Before `get_secret.py` returns the value, it sniffs the prefix to make sure it matches what that provider's keys actually look like.

## The provider prefixes

| Provider | Key prefix(es) | Where to get |
|----------|----------------|--------------|
| OpenAI | `sk-proj-`, `sk-svcacct-`, `sk-` | https://platform.openai.com/api-keys |
| Anthropic | `sk-ant-` | https://console.anthropic.com/settings/keys |
| OpenRouter | `sk-or-` | https://openrouter.ai/keys |
| Google Gemini | `AIzaSy` | https://aistudio.google.com/apikey |

These are stable, documented, and have been the same for years. Validation is just a `startswith()` check.

## What validation does

When you call `get_secret.py OPENAI_API_KEY`:

1. Retrieves the value from Keychain (or env/`.env`)
2. Checks: does the value start with `sk-proj-`, `sk-svcacct-`, or `sk-`?
3. If yes → returns the value
4. If no → checks if it starts with another known provider's prefix (`sk-or-`, `sk-ant-`, `AIzaSy`, etc.)
5. If yes → fails with a message like: *"OPENAI_API_KEY looks like an OpenRouter key (starts with `sk-or-`). Most likely OPENROUTER_API_KEY was stored under the OPENAI_API_KEY label by mistake. Fix: ..."*
6. If no known prefix matched → fails with: *"OPENAI_API_KEY has an unknown format (starts with `abc12345...`). Expected: sk-proj-XXXX"*

## Example: catching the mistake

```bash
# Accidentally store an OpenRouter key under the OpenAI label:
security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w 'sk-or-v1-real-openrouter-key'

# Try to use it:
python3 scripts/get_secret.py OPENAI_API_KEY
# →
# ERROR: OPENAI_API_KEY in Keychain looks like a OpenRouter key (starts with 'sk-or-').
# Most likely OPENROUTER_API_KEY was stored under the OPENAI_API_KEY label by mistake.
# Fix:
#   1) Get the real OPENAI_API_KEY: sk-proj-XXXX (from https://platform.openai.com/api-keys)
#   2) Overwrite the wrong entry:
#      security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w '<your-key>'
#   3) Verify: python3 scripts/get_secret.py OPENAI_API_KEY | head -c 12
```

The fix is right in the error. No API round-trip, no `401`, no debugging your code.

## Why this matters in practice

When you juggle 4-5 AI providers, the mistake **will** happen. Real scenarios:

- You paste a key from a provider dashboard into a `security add-generic-password` command, but accidentally swap two argument values
- A teammate adds a key to the wrong label in shared docs
- You rotate one provider's key and copy it into the wrong slot
- A migration script (incl. `setup_keyring.py`) reads `.env` lines and a row was mistyped

Without prefix validation, you spend an hour debugging your code while the provider keeps returning `401`. With it, you see the actual problem in the next command.

## Disabling validation

For keys not in `PROVIDER_FORMAT` (e.g. `STRIPE_API_KEY`, `INTERNAL_TOKEN`, anything custom), validation is skipped automatically — there's no spec to match against.

For known providers, if you have a reason to bypass (testing, migration), pass `--no-validate`:

```bash
python3 scripts/get_secret.py OPENAI_API_KEY --no-validate
```

This returns whatever's stored, no checks. Don't use this in production code — it defeats the whole point.

## Adding a new provider

Edit `PROVIDER_FORMAT` in `scripts/get_secret.py`:

```python
"NEW_PROVIDER_KEY": {
    "valid_prefixes": ("nv-",),                          # what valid keys start with
    "wrong_provider_hints": {                            # other prefixes → suggest the real label
        "sk-proj-": ("OPENAI_API_KEY", "OpenAI project key"),
        "sk-or-":   ("OPENROUTER_API_KEY", "OpenRouter"),
    },
    "example": "nv-XXXX (from https://newprovider.example.com/keys)",
},
```

The pattern is: list valid prefixes for that key's label, then list other providers' prefixes you want to catch (so the error can suggest the right label).
