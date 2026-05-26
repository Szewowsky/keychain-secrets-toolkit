#!/usr/bin/env python3
"""
Fetch a secret from macOS Keychain.

Fallback chain: Keychain -> env var -> .env file

Usage:
    python3 scripts/get_secret.py KEY_NAME

Shell substitution (recommended):
    curl -H "Authorization: Bearer $(python3 scripts/get_secret.py OPENAI_API_KEY)" ...

Service name:
    Default service is "my-secrets". Override with KEYCHAIN_SERVICE env var:
        KEYCHAIN_SERVICE=my-project python3 scripts/get_secret.py OPENAI_API_KEY

Per-provider prefix validation:
    For known AI providers (OpenAI, Anthropic, OpenRouter, Gemini), the script
    validates that the value matches the expected prefix. If you accidentally
    stored a wrong-provider key under the wrong label (e.g. an OpenRouter key
    under OPENAI_API_KEY), the script fails fast with a clear message instead
    of letting the API return a generic 401.

    Disable validation: --no-validate (useful for tests or migration).

See docs/prefix-validation.md for details.
"""
from __future__ import annotations  # PEP 604 (`str | None`) on Python 3.9 needs lazy eval

import sys
import os

DEFAULT_SERVICE = "my-secrets"


def get_service() -> str:
    return os.environ.get("KEYCHAIN_SERVICE", DEFAULT_SERVICE)


# Per-provider key format spec.
# wrong_provider_hints: if value starts with one of these prefixes, suggest the correct label.
PROVIDER_FORMAT = {
    "OPENAI_API_KEY": {
        "valid_prefixes": ("sk-proj-", "sk-svcacct-", "sk-"),
        "wrong_provider_hints": {
            "sk-or-": ("OPENROUTER_API_KEY", "OpenRouter"),
            "sk-ant-": ("ANTHROPIC_API_KEY", "Anthropic"),
            "AIzaSy": ("GEMINI_API_KEY", "Google Gemini"),
            "ya29.": ("GOOGLE_OAUTH_TOKEN", "Google OAuth (not an API key)"),
            '{"': ("OAUTH_JSON_BLOB", "OAuth JSON blob (not an API key — rotate completely)"),
        },
        "example": "sk-proj-XXXX (from https://platform.openai.com/api-keys)",
    },
    "OPENROUTER_API_KEY": {
        "valid_prefixes": ("sk-or-",),
        "wrong_provider_hints": {
            "sk-proj-": ("OPENAI_API_KEY", "OpenAI project key"),
            "sk-ant-": ("ANTHROPIC_API_KEY", "Anthropic"),
            "AIzaSy": ("GEMINI_API_KEY", "Google Gemini"),
        },
        "example": "sk-or-v1-XXXX (from https://openrouter.ai/keys)",
    },
    "ANTHROPIC_API_KEY": {
        "valid_prefixes": ("sk-ant-",),
        "wrong_provider_hints": {
            "sk-proj-": ("OPENAI_API_KEY", "OpenAI project key"),
            "sk-or-": ("OPENROUTER_API_KEY", "OpenRouter"),
        },
        "example": "sk-ant-XXXX (from https://console.anthropic.com/settings/keys)",
    },
    "GEMINI_API_KEY": {
        "valid_prefixes": ("AIzaSy",),
        "wrong_provider_hints": {
            "sk-proj-": ("OPENAI_API_KEY", "OpenAI project key"),
            "sk-or-": ("OPENROUTER_API_KEY", "OpenRouter"),
            "sk-ant-": ("ANTHROPIC_API_KEY", "Anthropic"),
        },
        "example": "AIzaSy... (from https://aistudio.google.com/apikey)",
    },
}


def validate_format(key_name: str, value: str) -> None:
    """Check prefix matches expected provider format. Fail fast with a clear message."""
    spec = PROVIDER_FORMAT.get(key_name)
    if not spec:
        return  # unknown provider -> no validation

    service = get_service()

    # 1. Cross-provider mismatch (most common mistake — wrong provider key under this label)
    for wrong_prefix, (correct_label, provider_name) in spec["wrong_provider_hints"].items():
        if value.startswith(wrong_prefix):
            sys.exit(
                f"ERROR: {key_name} in Keychain looks like a {provider_name} key (starts with '{wrong_prefix}').\n"
                f"Most likely {correct_label} was stored under the {key_name} label by mistake.\n"
                f"Fix:\n"
                f"  1) Get the real {key_name}: {spec['example']}\n"
                f"  2) Overwrite the wrong entry:\n"
                f"     security add-generic-password -U -a {key_name} -s {service} -w '<your-key>'\n"
                f"  3) Verify: python3 scripts/get_secret.py {key_name} | head -c 12\n"
                f"See docs/troubleshooting.md for more."
            )

    # 2. Unknown format (doesn't match any expected prefix)
    if not any(value.startswith(p) for p in spec["valid_prefixes"]):
        prefix_preview = value[:8] if len(value) >= 8 else value
        sys.exit(
            f"ERROR: {key_name} has an unknown format (starts with '{prefix_preview}...').\n"
            f"Expected format: {spec['example']}\n"
            f"Accepted prefixes: {', '.join(spec['valid_prefixes'])}\n"
            f"See docs/troubleshooting.md."
        )


def get_from_keychain(key_name: str) -> str | None:
    """Read from Keychain.

    Lookup chain (in order):
    1. security CLI: service=$KEYCHAIN_SERVICE, account=key_name
    2. Python keyring fallback: service=$KEYCHAIN_SERVICE
       (security CLI with -w returns an empty string for blob-format entries
        created by `keyring.set_password()`; keyring can read those.)
    """
    import subprocess
    service = get_service()

    # 1. security CLI (account=KEY_NAME convention — clean, scriptable)
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-a", key_name, "-s", service, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass

    # 2. Python keyring fallback (blob format — entries added via keyring.set_password())
    try:
        import keyring
        v = keyring.get_password(service, key_name)
        if v:
            return v
    except ImportError:
        pass

    return None


def get_from_env_file(key_name: str) -> str | None:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_path = os.path.normpath(env_path)
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key_name:
                    v = v.strip()
                    if v and v != "STORED_IN_KEYRING":
                        return v
    return None


def get_secret(key_name: str, validate: bool = True) -> str:
    # 1. Keychain
    value = get_from_keychain(key_name)
    if value:
        if validate:
            validate_format(key_name, value)
        return value

    # 2. Environment variable
    value = os.environ.get(key_name)
    if value and value != "STORED_IN_KEYRING":
        if validate:
            validate_format(key_name, value)
        return value

    # 3. .env file (backward compat)
    value = get_from_env_file(key_name)
    if value:
        if validate:
            validate_format(key_name, value)
        return value

    service = get_service()
    print(
        f"ERROR: Secret '{key_name}' not found.\n"
        f"Searched: Keychain (service='{service}'), env var, .env file.\n"
        f"Add it with:\n"
        f"  security add-generic-password -U -a {key_name} -s {service} -w '<your-key>'\n"
        f"Or interactively (recommended — key never lands in shell history):\n"
        f"  python3 -c \"import keyring; keyring.set_password('{service}', '{key_name}', input('Key: '))\"",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    validate = True
    if "--no-validate" in args:
        validate = False
        args = [a for a in args if a != "--no-validate"]

    if len(args) != 1:
        print("Usage: python3 get_secret.py KEY_NAME [--no-validate]", file=sys.stderr)
        sys.exit(1)

    secret = get_secret(args[0], validate=validate)
    print(secret, end="")
