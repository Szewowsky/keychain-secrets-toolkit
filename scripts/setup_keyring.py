#!/usr/bin/env python3
"""
Migracja sekretów do pęku kluczy macOS (Keychain).

Dwa tryby:

1. Masowa migracja z .env (gdy masz już gdzieś klucze):
       python3 scripts/setup_keyring.py

   Odczytuje .env, zapisuje każdą wartość w Keychain, nadpisuje wartości w .env
   placeholderami STORED_IN_KEYRING. Prosi o potwierdzenie przed zapisem.

2. Tryb interaktywny (zalecany — klucze nigdy nie trafiają do historii powłoki ani plików):
       python3 scripts/setup_keyring.py --interactive

   Pyta o każdy klucz z .env.example, odczytuje wartość przez input(),
   zapisuje bezpośrednio do Keychain. Plik .env NIE jest modyfikowany (możesz go
   zachować jako listę placeholderów).

Nazwa usługi:
    Domyślna usługa to "my-secrets". Nadpisz zmienną środowiskową KEYCHAIN_SERVICE:
        KEYCHAIN_SERVICE=my-project python3 scripts/setup_keyring.py
"""
import os
import sys
import getpass

try:
    import keyring
except ImportError:
    print("BŁĄD: najpierw zainstaluj zależności → pip3 install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

DEFAULT_SERVICE = "my-secrets"
PLACEHOLDER = "STORED_IN_KEYRING"


def get_service() -> str:
    return os.environ.get("KEYCHAIN_SERVICE", DEFAULT_SERVICE)


def parse_env_file(path: str, only_keys: bool = False) -> tuple[dict[str, str], list[str]]:
    """Zwraca (secrets_with_values, raw_lines). Jeśli only_keys=True, zwraca pusty słownik wartości,
    ale dołącza klucze jako listę (bez parsowania wartości)."""
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
    """Odczytuje .env, zapisuje wartości w Keychain, zastępuje .env placeholderami."""
    secrets, lines = parse_env_file(env_path)
    service = get_service()

    if not secrets:
        print(f"Brak sekretów do migracji z {env_path} (wszystkie to już STORED_IN_KEYRING lub .env jest pusty).")
        print(f"Zamiast tego spróbuj trybu interaktywnego: python3 scripts/setup_keyring.py --interactive")
        sys.exit(0)

    print(f"Znaleziono {len(secrets)} sekret(ów) w {env_path}:\n")
    for key, value in secrets.items():
        preview = value[:4] + "..." if len(value) > 4 else value
        print(f"  {key} = {preview}")

    print(f"\nCel: pęk kluczy macOS (usługa: '{service}')")
    confirm = input("\nKontynuować? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Przerwano.")
        sys.exit(0)

    print()
    for key, value in secrets.items():
        keyring.set_password(service, key, value)
        stored = keyring.get_password(service, key)
        if stored == value:
            preview = stored[:4] + "..."
            print(f"  OK   {key} -> Keychain ({preview})")
        else:
            print(f"  BŁĄD {key} -> weryfikacja nie powiodła się!")
            sys.exit(1)

    with open(env_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nZaktualizowano .env -> wszystkie wartości zastąpiono '{PLACEHOLDER}'")
    print(f"Weryfikacja: python3 scripts/get_secret.py <KEY_NAME>")


def interactive_setup(example_path: str) -> None:
    """Pyta o każdy klucz z .env.example, odczytuje wartości przez input(), zapisuje w Keychain.
    Klucze nigdy nie trafiają do historii powłoki ani plików — idą prosto z terminala do Keychain."""
    _, raw_lines = parse_env_file(example_path)
    service = get_service()

    # Wyodrębnij tylko nazwy kluczy z .env.example
    keys = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            keys.append(line.split("=", 1)[0].strip())

    if not keys:
        print(f"Nie znaleziono kluczy w {example_path}. Najpierw dodaj linie typu 'OPENAI_API_KEY=STORED_IN_KEYRING'.")
        sys.exit(1)

    print(f"Konfiguracja interaktywna — usługa: '{service}'")
    print(f"Znaleziono {len(keys)} klucz(y) w {example_path}.")
    print("Naciśnij Enter, aby pominąć klucz. Wartości nie są wyświetlane ani zapisywane w historii powłoki.\n")

    saved = 0
    for key in keys:
        value = getpass.getpass(f"  {key}: ")
        if not value:
            print(f"  -- pominięto {key}")
            continue
        keyring.set_password(service, key, value)
        stored = keyring.get_password(service, key)
        if stored == value:
            print(f"  OK {key} -> Keychain ({value[:4]}...)")
            saved += 1
        else:
            print(f"  BŁĄD {key} -> weryfikacja nie powiodła się!")
            sys.exit(1)

    print(f"\nGotowe. Zapisano {saved}/{len(keys)} klucz(y).")
    print(f"Weryfikacja: python3 scripts/get_secret.py <KEY_NAME>")


def main():
    interactive = "--interactive" in sys.argv

    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(repo_root, ".env")
    example_path = os.path.join(repo_root, ".env.example")

    if interactive:
        if not os.path.exists(example_path):
            print(f"BŁĄD: nie znaleziono {example_path}. Najpierw go utwórz (zobacz README).", file=sys.stderr)
            sys.exit(1)
        interactive_setup(example_path)
    else:
        if not os.path.exists(env_path):
            print(f"BŁĄD: nie znaleziono {env_path}.\nMożesz:\n  - Skopiować .env.example do .env i dodać prawdziwe wartości, a następnie uruchomić ponownie\n  - Albo użyć trybu interaktywnego: python3 scripts/setup_keyring.py --interactive", file=sys.stderr)
            sys.exit(1)
        bulk_migrate(env_path)


if __name__ == "__main__":
    main()
