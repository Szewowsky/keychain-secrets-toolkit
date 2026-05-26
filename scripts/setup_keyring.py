#!/usr/bin/env python3
"""
Migrate secrets to macOS Keychain.

Two modes:

1. Bulk migration from .env (when you already have keys somewhere):
       python3 scripts/setup_keyring.py

   Reads .env, stores each value in Keychain, overwrites .env values with
   STORED_IN_KEYRING placeholders. Asks for confirmation before writing.

2. Interactive mode (recommended — keys never land in shell history or files):
       python3 scripts/setup_keyring.py --interactive

   Prompts for each key listed in .env.example, reads value via input(),
   writes directly to Keychain. The .env file is NOT touched (you can keep
   it as a list of placeholders).

Service name:
    Default service is "my-secrets". Override with KEYCHAIN_SERVICE env var:
        KEYCHAIN_SERVICE=my-project python3 scripts/setup_keyring.py
"""
import os
import sys
import getpass

try:
    import keyring
except ImportError:
    print("ERROR: install dependencies first → pip3 install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

DEFAULT_SERVICE = "my-secrets"
PLACEHOLDER = "STORED_IN_KEYRING"


def get_service() -> str:
    return os.environ.get("KEYCHAIN_SERVICE", DEFAULT_SERVICE)


def parse_env_file(path: str, only_keys: bool = False) -> tuple[dict[str, str], list[str]]:
    """Return (secrets_with_values, raw_lines). If only_keys=True, return empty values dict
    but include keys as list (no parsing of values)."""
    secrets = {}
    lines = []
    if not os.path.exists(path):
        return secrets, lines
    with open(path, "r") as f:
        for line in f:
            raw = line.rstrip("\n")
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(raw)
                continue
            if "=" in stripped:
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value and value != PLACEHOLDER:
                    secrets[key] = value
                lines.append(f"{key}={PLACEHOLDER}")
            else:
                lines.append(raw)
    return secrets, lines


def bulk_migrate(env_path: str) -> None:
    """Read .env, store values in Keychain, replace .env with placeholders."""
    secrets, lines = parse_env_file(env_path)
    service = get_service()

    if not secrets:
        print(f"No secrets to migrate from {env_path} (all already STORED_IN_KEYRING or .env empty).")
        print(f"Try interactive mode instead: python3 scripts/setup_keyring.py --interactive")
        sys.exit(0)

    print(f"Found {len(secrets)} secret(s) in {env_path}:\n")
    for key, value in secrets.items():
        preview = value[:4] + "..." if len(value) > 4 else value
        print(f"  {key} = {preview}")

    print(f"\nTarget: macOS Keychain (service: '{service}')")
    confirm = input("\nProceed? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    print()
    for key, value in secrets.items():
        keyring.set_password(service, key, value)
        stored = keyring.get_password(service, key)
        if stored == value:
            preview = stored[:4] + "..."
            print(f"  OK   {key} -> Keychain ({preview})")
        else:
            print(f"  FAIL {key} -> verification failed!")
            sys.exit(1)

    with open(env_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n.env updated -> all values replaced with '{PLACEHOLDER}'")
    print(f"Verify: python3 scripts/get_secret.py <KEY_NAME>")


def interactive_setup(example_path: str) -> None:
    """Prompt for each key in .env.example, read values via input(), store in Keychain.
    Keys never land in shell history or files — they go straight from terminal to Keychain."""
    _, raw_lines = parse_env_file(example_path)
    service = get_service()

    # Extract just the key names from .env.example
    keys = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            keys.append(line.split("=", 1)[0].strip())

    if not keys:
        print(f"No keys found in {example_path}. Add lines like 'OPENAI_API_KEY=STORED_IN_KEYRING' first.")
        sys.exit(1)

    print(f"Interactive setup — service: '{service}'")
    print(f"Found {len(keys)} key(s) in {example_path}.")
    print("Press Enter to skip a key. Values are not echoed and not stored in shell history.\n")

    saved = 0
    for key in keys:
        value = getpass.getpass(f"  {key}: ")
        if not value:
            print(f"  -- skipped {key}")
            continue
        keyring.set_password(service, key, value)
        stored = keyring.get_password(service, key)
        if stored == value:
            print(f"  OK {key} -> Keychain ({value[:4]}...)")
            saved += 1
        else:
            print(f"  FAIL {key} -> verification failed!")
            sys.exit(1)

    print(f"\nDone. {saved}/{len(keys)} key(s) stored.")
    print(f"Verify: python3 scripts/get_secret.py <KEY_NAME>")


def main():
    interactive = "--interactive" in sys.argv

    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(repo_root, ".env")
    example_path = os.path.join(repo_root, ".env.example")

    if interactive:
        if not os.path.exists(example_path):
            print(f"ERROR: {example_path} not found. Create it first (see README).", file=sys.stderr)
            sys.exit(1)
        interactive_setup(example_path)
    else:
        if not os.path.exists(env_path):
            print(f"ERROR: {env_path} not found.\nEither:\n  - Copy .env.example to .env and add real values, then re-run\n  - Or use interactive mode: python3 scripts/setup_keyring.py --interactive", file=sys.stderr)
            sys.exit(1)
        bulk_migrate(env_path)


if __name__ == "__main__":
    main()
