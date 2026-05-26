#!/usr/bin/env python3
"""
Przykład: wywołanie get_secret.py z Pythona przez subprocess.

Dwa wzorce:

1. subprocess.run() — jawny, zwraca string. Użyj, gdy potrzebujesz klucza
   w swoim kodzie Python (np. do przekazania do SDK).

2. Bezpośredni import — jeśli dodałeś `scripts/` do PYTHONPATH lub zainstalowałeś
   toolkit jako pakiet. Nieco szybsze (brak subprocess).

Oba są równie bezpieczne: klucz nigdy nie trafia do historii powłoki ani na stdout.
"""
import os
import subprocess
import sys

# Ścieżka do katalogu skryptów toolkitu (dostosuj, jeśli skopiowałeś skrypt
# w inne miejsce lub zainstalowałeś inaczej)
SCRIPTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)


def get_secret(key_name: str) -> str:
    """Wzorzec subprocess — działa, dopóki toolkit znajduje się gdzieś na dysku."""
    result = subprocess.run(
        ["python3", os.path.join(SCRIPTS_DIR, "get_secret.py"), key_name],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# Przykładowe użycie:
if __name__ == "__main__":
    openai_key = get_secret("OPENAI_API_KEY")
    print(f"Klucz OpenAI zaczyna się od: {openai_key[:8]}...")  # bezpieczne logowanie prefiksu

    # Teraz użyj go z dowolnym SDK, np.:
    #
    #     from openai import OpenAI
    #     client = OpenAI(api_key=openai_key)
    #     ...
    #
    # Albo ustaw jako zmienną środowiskową dla bibliotek, które wykrywają ją automatycznie:
    #     os.environ["OPENAI_API_KEY"] = openai_key
