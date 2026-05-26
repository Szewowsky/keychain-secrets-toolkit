# Rozwiązywanie problemów

Częste problemy i sposoby ich diagnozowania.

## `BŁĄD: Nie znaleziono sekretu 'XYZ'`

Kolejność prawdopodobnych przyczyn (od najczęstszych):

1. **Zła nazwa usługi.** Zestaw narzędzi domyślnie używa usługi `my-secrets`. Jeśli zapisałeś klucz pod inną usługą, ustaw zmienną środowiskową:
   ```bash
   KEYCHAIN_SERVICE=your-service-name python3 scripts/get_secret.py XYZ
   ```

2. **Klucz znajduje się pod `label` zamiast `account`.** Starsze konwencje używały `-l KEY_NAME` (label) zamiast `-a KEY_NAME` (account). Nowy zestaw narzędzi używa `account=KEY_NAME`. Aby zmigrować:
   ```bash
   # Odczyt ze starej lokalizacji (z label):
   security find-generic-password -a robert -s my-secrets -l XYZ -w

   # Zapis do nowej lokalizacji (z account):
   security add-generic-password -U -a XYZ -s my-secrets -w '<value>'
   ```

3. **Dodałeś klucz, ale się nie pojawia.** Zweryfikuj:
   ```bash
   security find-generic-password -a XYZ -s my-secrets -w
   ```
   Jeśli to polecenie zwraca pusty wynik, ale możesz znaleźć klucz w aplikacji Keychain Access, być może zapisałeś go przez `keyring.set_password()` (format blob). Fallback w Pythonie w `get_secret.py` go odczyta, ale samo CLI `security` nie.

## `BŁĄD: XYZ ma nieznany format`

Wartość w Keychain nie zaczyna się od żadnego z oczekiwanych prefiksów dla tego dostawcy. Przyczyny:

- Zapisałeś **klucz niewłaściwego dostawcy** pod tą etykietą. Zobacz [prefix-validation.md](prefix-validation.md) — komunikat o błędzie zasugeruje, jakiej etykiety użyć zamiast niej.
- Klucz jest **ucięty**. Uruchom:
  ```bash
  python3 scripts/get_secret.py XYZ --no-validate | wc -c
  ```
  Większość kluczy API AI ma 50-200 znaków. Jeśli widzisz <20, klucz jest ucięty.
- Klucz został **zapisany z cudzysłowami**. Niektóre powłoki zachowują cudzysłowy wewnątrz `-w '...'`. Zapisz ponownie bez nich:
  ```bash
  # Źle (dosłowne cudzysłowy):
  security add-generic-password -U -a XYZ -s my-secrets -w "'sk-proj-XXX'"

  # Poprawnie (pojedyncze cudzysłowy konsumowane przez powłokę):
  security add-generic-password -U -a XYZ -s my-secrets -w 'sk-proj-XXX'
  ```

## `401 Unauthorized` z API, mimo że klucz jest w Keychain

Kolejność diagnostyki:

1. **Czy `--no-validate` jest potrzebne?** Jeśli tak, używasz klucza z niestandardowym prefiksem, którego zestaw narzędzi nie zna. Przejdź do kroku 3.
2. **Czy `get_secret.py` faktycznie zwrócił to, czego oczekujesz?** Wypisz pierwsze 12 znaków (to bezpieczne — to tylko prefiks):
   ```bash
   python3 scripts/get_secret.py XYZ | head -c 12
   ```
   Porównaj z prefiksem, którego się spodziewasz.
3. **Czy klucz został unieważniony?** Sprawdź dashboard dostawcy. Klucze są często unieważniane podczas rotacji, gdy zapomnisz, który z nich był nowy.
4. **Czy klucz jest dla właściwego konta/workspace'u?** Niektórzy dostawcy (OpenAI, Anthropic) mają klucze o zasięgu projektu. Klucz projektu dla projektu A zwróci `401` dla żądań z projektu B.
5. **Tokeny OAuth a klucze API.** Tokeny takie jak `ya29.a0Aa...` (Google) lub `gho_...` (GitHub) **wygasają**. To nie są klucze API. Jeśli zapisałeś token OAuth pod etykietą `_API_KEY`, będzie działał przez jakiś czas, a potem przestanie w momencie wygaśnięcia. Zastąp go prawdziwym kluczem API (lub zaimplementuj trwały mechanizm odświeżania OAuth).

## Keychain pyta o hasło za każdym razem

Aplikacja Keychain Access domyślnie odblokowuje się przy logowaniu. Jeśli pyta o hasło przy każdym poleceniu:

1. Otwórz aplikację **Keychain Access**
2. Kliknij wpis prawym przyciskiem myszy → **Get Info** → zakładka **Access Control**
3. Dodaj `/usr/bin/security` oraz `/usr/bin/python3` do **Always allow access by these applications**

Dla maksymalnej wygody: ustaw "Allow all applications" — ale tylko na maszynach deweloperskich, nie na współdzielonych/służbowych.

## `pip install keyring` kończy się błędem `externally-managed-environment`

Python 3.12+ w systemie macOS wymusza PEP 668. Opcje:

```bash
# Opcja 1 — instalacja użytkownika (zalecane dla narzędzi osobistych):
pip3 install --user keyring

# Opcja 2 — środowisko wirtualne (zalecane dla projektów):
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Opcja 3 — Python z Homebrew (znosi wymuszanie PEP 668):
brew install python && pip3 install keyring

# Opcja 4 — tylko jeśli akceptujesz ryzyko:
pip3 install --break-system-packages keyring
```

Większość użytkowników wybierze opcję 1 lub 2.

## Skrypt wrapper zawodzi: "command not found" lub "permission denied"

```bash
chmod 755 scripts/mcp-*-wrapper.sh
```

Sprawdź również **pierwszą linię** wrappera (`#!/bin/bash`) — jeśli ma windowsowe zakończenia linii (`\r\n`), bash nie będzie w stanie jej sparsować. Naprawa:

```bash
sed -i '' 's/\r$//' scripts/mcp-*-wrapper.sh
```

## Przypadkowo wkleiłem klucz do czatu AI / zacommitowałem go

Zobacz **[security-first.md](security-first.md)** — "Jeśli klucz i tak wycieknie".

TL;DR: natychmiast zrotuj klucz w dashboardzie dostawcy. Nie próbuj czyścić historii git — cache i forki sprawiają, że stare commity wciąż są dostępne. Klucz jest skompromitowany w momencie, gdy opuszcza Twój terminal; jedynym rozwiązaniem jest rotacja.

## Dodawanie logowania diagnostycznego

Jeśli `get_secret.py` w tajemniczy sposób zwraca błędne wartości lub nie zwraca nic, dodaj tymczasowe logowanie debugowania:

```python
# Na górze get_secret.py:
import sys
DEBUG = True

# Wewnątrz get_from_keychain:
if DEBUG:
    print(f"[debug] trying security CLI: account={key_name} service={service}", file=sys.stderr)
```

Loguje to do stderr, więc nie zanieczyszcza wartości stdout (samego klucza). Usuń po zakończeniu.
