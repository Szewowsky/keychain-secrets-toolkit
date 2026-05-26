#!/usr/bin/env python3
"""
Pobierz sekret z pęku kluczy macOS (Keychain).

Łańcuch awaryjny: Keychain -> zmienna środowiskowa -> plik .env

Użycie:
    python3 scripts/get_secret.py KEY_NAME

Podstawienie w powłoce (zalecane):
    curl -H "Authorization: Bearer $(python3 scripts/get_secret.py OPENAI_API_KEY)" ...

Nazwa usługi:
    Domyślna usługa to "my-secrets". Nadpisz za pomocą zmiennej środowiskowej KEYCHAIN_SERVICE:
        KEYCHAIN_SERVICE=my-project python3 scripts/get_secret.py OPENAI_API_KEY

Walidacja prefiksów dla poszczególnych dostawców:
    Dla znanych dostawców AI (OpenAI, Anthropic, OpenRouter, Gemini), skrypt
    sprawdza, czy wartość pasuje do oczekiwanego prefiksu. Jeśli przypadkowo
    zapisano klucz niewłaściwego dostawcy pod złą etykietą (np. klucz OpenRouter
    jako OPENAI_API_KEY), skrypt szybko kończy działanie z jasnym komunikatem,
    zamiast pozwalać API na zwrócenie ogólnego błędu 401.

    Wyłączenie walidacji: --no-validate (przydatne w testach lub podczas migracji).

Zobacz docs/prefix-validation.md, aby uzyskać szczegóły.
"""
from __future__ import annotations  # PEP 604 (`str | None`) w Pythonie 3.9 wymaga leniwej ewaluacji

import sys
import os

DEFAULT_SERVICE = "my-secrets"


def get_service() -> str:
    return os.environ.get("KEYCHAIN_SERVICE", DEFAULT_SERVICE)


# Specyfikacja formatu klucza dla poszczególnych dostawców.
# wrong_provider_hints: jeśli wartość zaczyna się od jednego z tych prefiksów, zasugeruj poprawną etykietę.
PROVIDER_FORMAT = {
    "OPENAI_API_KEY": {
        "valid_prefixes": ("sk-proj-", "sk-svcacct-", "sk-"),
        "wrong_provider_hints": {
            "sk-or-": ("OPENROUTER_API_KEY", "OpenRouter"),
            "sk-ant-": ("ANTHROPIC_API_KEY", "Anthropic"),
            "AIzaSy": ("GEMINI_API_KEY", "Google Gemini"),
            "ya29.": ("GOOGLE_OAUTH_TOKEN", "Google OAuth (to nie jest klucz API)"),
            '{"': ("OAUTH_JSON_BLOB", "Obiekt JSON OAuth (to nie jest klucz API — wymień go całkowicie)"),
        },
        "example": "sk-proj-XXXX (z https://platform.openai.com/api-keys)",
    },
    "OPENROUTER_API_KEY": {
        "valid_prefixes": ("sk-or-",),
        "wrong_provider_hints": {
            "sk-proj-": ("OPENAI_API_KEY", "klucz projektu OpenAI"),
            "sk-ant-": ("ANTHROPIC_API_KEY", "Anthropic"),
            "AIzaSy": ("GEMINI_API_KEY", "Google Gemini"),
        },
        "example": "sk-or-v1-XXXX (z https://openrouter.ai/keys)",
    },
    "ANTHROPIC_API_KEY": {
        "valid_prefixes": ("sk-ant-",),
        "wrong_provider_hints": {
            "sk-proj-": ("OPENAI_API_KEY", "klucz projektu OpenAI"),
            "sk-or-": ("OPENROUTER_API_KEY", "OpenRouter"),
        },
        "example": "sk-ant-XXXX (z https://console.anthropic.com/settings/keys)",
    },
    "GEMINI_API_KEY": {
        "valid_prefixes": ("AIzaSy",),
        "wrong_provider_hints": {
            "sk-proj-": ("OPENAI_API_KEY", "klucz projektu OpenAI"),
            "sk-or-": ("OPENROUTER_API_KEY", "OpenRouter"),
            "sk-ant-": ("ANTHROPIC_API_KEY", "Anthropic"),
        },
        "example": "AIzaSy... (z https://aistudio.google.com/apikey)",
    },
}


def validate_format(key_name: str, value: str) -> None:
    """Sprawdź, czy prefiks pasuje do oczekiwanego formatu dostawcy. Szybko zakończ z jasnym komunikatem."""
    spec = PROVIDER_FORMAT.get(key_name)
    if not spec:
        return  # nieznany dostawca -> brak walidacji

    service = get_service()

    # 1. Niezgodność dostawcy (najczęstszy błąd — klucz złego dostawcy pod tą etykietą)
    for wrong_prefix, (correct_label, provider_name) in spec["wrong_provider_hints"].items():
        if value.startswith(wrong_prefix):
            sys.exit(
                f"BŁĄD: {key_name} w Keychain wygląda jak klucz {provider_name} (zaczyna się od '{wrong_prefix}').\n"
                f"Najprawdopodobniej {correct_label} został omyłkowo zapisany pod etykietą {key_name}.\n"
                f"Naprawa:\n"
                f"  1) Pobierz prawdziwy {key_name}: {spec['example']}\n"
                f"  2) Nadpisz błędny wpis:\n"
                f"     security add-generic-password -U -a {key_name} -s {service} -w '<your-key>'\n"
                f"  3) Zweryfikuj: python3 scripts/get_secret.py {key_name} | head -c 12\n"
                f"Zobacz docs/troubleshooting.md, aby dowiedzieć się więcej."
            )

    # 2. Nieznany format (nie pasuje do żadnego oczekiwanego prefiksu)
    if not any(value.startswith(p) for p in spec["valid_prefixes"]):
        prefix_preview = value[:8] if len(value) >= 8 else value
        sys.exit(
            f"BŁĄD: {key_name} ma nieznany format (zaczyna się od '{prefix_preview}...').\n"
            f"Oczekiwany format: {spec['example']}\n"
            f"Akceptowane prefiksy: {', '.join(spec['valid_prefixes'])}\n"
            f"Zobacz docs/troubleshooting.md."
        )


def get_from_keychain(key_name: str) -> str | None:
    """Odczytaj z pęku kluczy (Keychain).

    Łańcuch wyszukiwania (w kolejności):
    1. CLI security: service=$KEYCHAIN_SERVICE, account=key_name
    2. Fallback do pythonowego keyring: service=$KEYCHAIN_SERVICE
       (CLI security z flagą -w zwraca pusty ciąg dla wpisów w formacie blob
        utworzonych przez `keyring.set_password()`; keyring potrafi je odczytać.)
    """
    import subprocess
    service = get_service()

    # 1. CLI security (konwencja account=KEY_NAME — czyste, łatwe do skryptowania)
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-a", key_name, "-s", service, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass

    # 2. Fallback do pythonowego keyring (format blob — wpisy dodane przez keyring.set_password())
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
    # 1. Pęk kluczy (Keychain)
    value = get_from_keychain(key_name)
    if value:
        if validate:
            validate_format(key_name, value)
        return value

    # 2. Zmienna środowiskowa
    value = os.environ.get(key_name)
    if value and value != "STORED_IN_KEYRING":
        if validate:
            validate_format(key_name, value)
        return value

    # 3. Plik .env (kompatybilność wsteczna)
    value = get_from_env_file(key_name)
    if value:
        if validate:
            validate_format(key_name, value)
        return value

    service = get_service()
    print(
        f"BŁĄD: Nie znaleziono sekretu '{key_name}'.\n"
        f"Przeszukano: Keychain (service='{service}'), zmienną środowiskową, plik .env.\n"
        f"Dodaj go za pomocą:\n"
        f"  security add-generic-password -U -a {key_name} -s {service} -w '<your-key>'\n"
        f"Lub interaktywnie (zalecane — klucz nigdy nie trafia do historii powłoki):\n"
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
        print("Użycie: python3 get_secret.py KEY_NAME [--no-validate]", file=sys.stderr)
        sys.exit(1)

    secret = get_secret(args[0], validate=validate)
    print(secret, end="")
