# Łańcuch wyszukiwania — Jak `get_secret.py` znajduje Twoje klucze

`scripts/get_secret.py` przeszukuje trzy źródła w określonej kolejności. Zwraca pierwsze, które dostarczy wartość. Zrozumienie tej kolejności ma znaczenie, gdy coś nie działa — będziesz dokładnie wiedzieć, gdzie szukać.

## Łańcuch

```
1. macOS Keychain (zalecane)
   service = $KEYCHAIN_SERVICE (domyślnie: "my-secrets")
   account = KEY_NAME
   ↓ (brak wartości)
2. Zmienna środowiskowa
   $KEY_NAME (ale tylko jeśli != "STORED_IN_KEYRING")
   ↓ (brak wartości)
3. Plik .env
   linia `KEY_NAME=value` (ale tylko jeśli value != "STORED_IN_KEYRING")
   ↓ (brak wartości)
BŁĄD — nie znaleziono klucza
```

## Krok 1: Keychain

Dwie podścieżki, sprawdzane w kolejności:

### 1a. CLI `security`

```bash
security find-generic-password -a KEY_NAME -s my-secrets -w
```

To jest kanoniczny sposób i to, co generują `setup_keyring.py` oraz `add-generic-password`. Szybki, łatwy do oskryptowania, natywny.

### 1b. Biblioteka Python `keyring` (fallback)

Niektóre narzędzia (starsze wersje biblioteki `keyring` w Pythonie lub ręcznie wywołane `keyring.set_password()`) zapisują wpisy w formacie "blob", dla którego `security ... -w` zwraca pusty wynik. Biblioteka Pythona `keyring` odczytuje je poprawnie.

Ten fallback jest automatyczny — nie musisz o nim myśleć. Istnieje po to, aby wyłapywać wpisy utworzone przez mieszane narzędzia.

## Krok 2: Zmienna środowiskowa

Jeśli klucza nie ma w Keychain, skrypt sprawdza `os.environ[KEY_NAME]`. Pozwala to systemom CI, kontenerom Docker lub jednorazowym sesjom powłoki na wstrzykiwanie kluczy przez środowisko bez konieczności dostępu do Keychain.

**Przypadek szczególny:** jeśli zmienna środowiskowa jest ustawiona dosłownie na `STORED_IN_KEYRING`, jest traktowana jako "nie znaleziona" — to konwencja dla placeholderów. Możesz użyć `source .env`, aby załadować wszystkie placeholdery do środowiska bez psucia łańcucha wyszukiwania.

## Krok 3: Plik `.env`

Ostatnia deska ratunku. Odczytuje plik `.env` w głównym katalogu repozytorium, parsuje linie `KEY=value`. Pomija:
- Puste linie
- Komentarze (`# ...`)
- Linie, w których `value == "STORED_IN_KEYRING"`

Służy to głównie kompatybilności wstecznej — jeśli jeszcze nie zmigrowałeś do Keychain, skrypt nadal działa. **Po migracji plik `.env` zawiera tylko placeholdery, więc ten krok zawsze nie zwraca niczego.** To jest docelowy, bezpieczny stan.

## Zmienna środowiskowa `KEYCHAIN_SERVICE`

Domyślnie wszystkie klucze znajdują się pod nazwą usługi Keychain `my-secrets`. Możesz to nadpisać dla każdego projektu:

```bash
# Powłoka:
KEYCHAIN_SERVICE=my-project python3 scripts/get_secret.py OPENAI_API_KEY

# Trwale dla Twojej sesji powłoki:
export KEYCHAIN_SERVICE=my-project

# W skrypcie wrapper (.zshrc lub per-projekt .envrc z direnv):
export KEYCHAIN_SERVICE="$(basename $(pwd))"
```

Pozwala to na separację kluczy per projekt: `acme-prod-keys`, `personal-secrets`, `client-x-keys` itp. Wszystko w tym samym macOS Keychain, oddzielone nazwą usługi.

## Dlaczego nie zapisujemy z powrotem do `.env`

Niektóre narzędzia automatycznie zapisują rozwiązane klucze z powrotem do pliku `.env` w celu cachowania. **Ten zestaw narzędzi celowo tego nie robi.** Ponieważ:
- Jeśli `.env` kiedykolwiek znów zawierałby prawdziwe wartości, ryzykowałbyś ponownym wyciekiem przy następnym commicie
- Keychain jest już wystarczająco szybki (mikrosekundy)
- Wzorzec z placeholderami sprawia, że przypadkowe commity są widoczne: prawdziwa wartość w `.env` po migracji to czerwona flaga

## Debugowanie: którą ścieżkę wybrał `get_secret.py`?

Jeśli klucz zwraca złą wartość lub `not found`, sprawdź źródła w kolejności:

```bash
# 1. Czy jest w Keychain?
security find-generic-password -a OPENAI_API_KEY -s my-secrets -w
# (zostaniesz poproszony o hasło logowania)

# 2. Czy jest w zmiennych środowiskowych?
echo "${OPENAI_API_KEY:-not-set}"

# 3. Czy jest w .env?
grep "^OPENAI_API_KEY=" .env
```

Jeśli `security find-generic-password` zwraca pusty wynik, ale Pythonowy `keyring` go znajduje, wpis jest w formacie blob — to właśnie dla tego przypadku istnieje fallback 1b.

## Zobacz również

- `docs/prefix-validation.md` — co się stanie, jeśli znaleziona wartość jest kluczem niewłaściwego dostawcy
- `docs/troubleshooting.md` — nieaktualne tokeny, obcinanie znaków, niezgodności między dostawcami
