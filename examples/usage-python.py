#!/usr/bin/env python3
"""
Example: calling get_secret.py from Python via subprocess.

Two patterns:

1. subprocess.run() — explicit, returns string. Use when you need the key
   in your Python code (e.g. passing to an SDK).

2. Direct import — if you've put `scripts/` on PYTHONPATH or installed the
   toolkit as a package. Slightly faster (no subprocess).

Both are equally safe: the key never lands in shell history or stdout.
"""
import os
import subprocess
import sys

# Path to the toolkit scripts directory (adjust if you've copied the script
# elsewhere or installed differently)
SCRIPTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)


def get_secret(key_name: str) -> str:
    """Subprocess pattern — works as long as the toolkit is on disk somewhere."""
    result = subprocess.run(
        ["python3", os.path.join(SCRIPTS_DIR, "get_secret.py"), key_name],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# Example usage:
if __name__ == "__main__":
    openai_key = get_secret("OPENAI_API_KEY")
    print(f"OpenAI key starts with: {openai_key[:8]}...")  # safe to log prefix

    # Now use it with any SDK, e.g.:
    #
    #     from openai import OpenAI
    #     client = OpenAI(api_key=openai_key)
    #     ...
    #
    # Or set it as env var for libraries that auto-detect:
    #     os.environ["OPENAI_API_KEY"] = openai_key
