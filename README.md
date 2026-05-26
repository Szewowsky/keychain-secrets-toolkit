# keychain-secrets-toolkit

Bezpieczne przechowywanie kluczy API do AI w macOS Keychain — plus wrappery do serwerów MCP w Claude Code.

Mały toolkit (dwa skrypty Pythona, szablon wrappera shellowego, kilka dokumentów) który trzyma Twoje klucze API z dala od plików `.env`, historii shella, screenshotów i transkryptów AI. Klucze żyją w macOS Keychain. Twój kod pobiera je pojedynczą komendą która nigdy nie ujawnia wartości.

> **Tylko macOS.** Toolkit polega na natywnym CLI `security` i Keychainie. Odpowiedniki Windows/Linux (Credential Manager, GNOME Keyring) teoretycznie działają przez bibliotekę Pythona `keyring`, ale skrypty nie zostały do nich zaadaptowane ani przetestowane.

## Po co to

Domyślny sposób w jaki developerzy przechowują klucze API do AI — wrzucają je do `.env`, potem przypadkiem commitują plik, albo wklejają wartość do ChatGPT "żeby zdebugować" — wycieka więcej kluczy tygodniowo niż wszystkie realne włamania razem wzięte. Ten toolkit:

- Trzyma klucze w macOS Keychain (vault na poziomie OS, odblokowywany Twoim hasłem logowania / Touch ID)
- Zastępuje wartości w `.env` placeholderami `STORED_IN_KEYRING`, więc plik jest bezpieczny do commitowania
- Daje jednolity skrypt do lookup'u — Twój kod nigdy nie widzi surowego klucza w źródle ani historii shella
- Łapie **pomyłki cross-provider** (jeśli klucz wygląda jak nie tego providera, fail-fast z instrukcją naprawy zamiast generycznego 401)
- Zawiera wzorzec wrappera dla MCP dla użytkowników Claude Code / serwerów MCP którzy nie mogą trzymać plaintext kluczy w `.mcp.json`

## Jedna zasada

> **Nigdy nie wklejaj klucza API do AI chatu (ChatGPT, Claude Code, Cursor, Gemini, czegokolwiek innego).**

Wklejenie klucza do narzędzia AI ląduje w kontekście sesji modelu, w logach pipeline'u providera i w transkrypcie Twojej konwersacji. Szkoda jest permanentna — jedyna naprawa to rotacja klucza.

Przeczytaj **[docs/security-first.md](docs/security-first.md)** zanim cokolwiek zrobisz. Jest krótki i kluczowy.

## Setup (5 minut)

### 1. Klonuj

```bash
git clone https://github.com/Szewowsky/keychain-secrets-toolkit.git
cd keychain-secrets-toolkit
pip3 install --user -r requirements.txt
```

(Albo użyj virtual env — patrz `docs/troubleshooting.md` jeśli `pip3 install` failuje.)

### 2. Dodaj swoje klucze (wybierz jedną metodę)

**Metoda A — Interaktywna (zalecana). Klucz nigdy nie ląduje w historii shella ani w żadnym pliku:**

```bash
python3 scripts/setup_keyring.py --interactive
```

Pyta o każdy klucz wymieniony w `.env.example`. Enter pomija te których nie masz.

**Metoda B — Natywne CLI macOS, jeden po drugim:**

```bash
security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w 'sk-proj-XXX'
security add-generic-password -U -a ANTHROPIC_API_KEY -s my-secrets -w 'sk-ant-XXX'
```

Cała komenda (włącznie z kluczem) ląduje w `~/.zsh_history`. Albo poprzedź komendę spacją (jeśli masz `HIST_IGNORE_SPACE` w shellu), albo uruchom `history -d $(history | tail -1 | awk '{print $1}')` żeby usunąć ostatni wpis.

**Metoda C — Migracja z istniejącego `.env`:**

```bash
# 1. Skopiuj .env.example, wpisz prawdziwe wartości
cp .env.example .env
# edytuj .env w ulubionym edytorze

# 2. Migruj (pyta o potwierdzenie):
python3 scripts/setup_keyring.py

# .env jest teraz nadpisany placeholderami STORED_IN_KEYRING.
```

### 3. Używaj

W skryptach shellowych:

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $(python3 scripts/get_secret.py OPENAI_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"cześć"}]}'
```

Shell rozwija `$(...)` zanim uruchomi `curl` — klucz przepływa z `python3` prosto do headera HTTP, nigdy nie pojawiając się na stdout.

W Pythonie:

```python
import subprocess

def get_secret(key_name):
    return subprocess.run(
        ["python3", "scripts/get_secret.py", key_name],
        capture_output=True, text=True, check=True
    ).stdout

openai_key = get_secret("OPENAI_API_KEY")
```

Więcej w `examples/usage-curl.sh` i `examples/usage-python.py`.

## Dlaczego dwa pliki: `.env.example` vs `.env`?

Klasyczny pattern devops, ale często niejasny dla osób nowych w temacie. Dwa pliki, dwie role:

```
.env.example   ← W REPO. Tylko placeholdery STORED_IN_KEYRING.
                 Bezpieczny do commitowania. Każdy kto clone'uje widzi nazwy kluczy
                 (ale NIE wartości — bo wartości tu nigdy nie ma).

.env           ← LOKALNIE TYLKO. Jest w .gitignore — nigdy nie idzie do gita.
                 Trafia tu prawdziwy klucz TYLKO przy migracji (Metoda C).
                 Po migracji jest nadpisany placeholderami STORED_IN_KEYRING.
```

### Co oznacza `STORED_IN_KEYRING`?

To jest **placeholder** (zaślepka), nie magia. Skrypt `get_secret.py` widzi że wartość = `STORED_IN_KEYRING` i wie: *"nie traktuj tego jako prawdziwego klucza, idź dalej po łańcuchu (Keychain → env var → koniec)"*.

Format każdej linii w `.env.example` i `.env`:

```bash
NAZWA_KLUCZA=STORED_IN_KEYRING
```

Przykład jak `.env` wygląda **po migracji** do Keychain (Metoda C) lub w `.env.example` (zawsze):

```bash
OPENAI_API_KEY=STORED_IN_KEYRING
ANTHROPIC_API_KEY=STORED_IN_KEYRING
OPENROUTER_API_KEY=STORED_IN_KEYRING
GEMINI_API_KEY=STORED_IN_KEYRING
```

Widać tylko **które klucze są zarządzane**, ale nie ich wartości. Plik jest bezpieczny lokalnie i nie wycieka nawet jeśli ktoś zobaczy zrzut ekranu Twojego terminala.

### Kiedy w ogóle potrzebujesz lokalnego `.env`?

Zależy od wybranej metody setupu. **W większości scenariuszy `.env` w ogóle Ci nie jest potrzebny:**

| Metoda | Tworzysz `.env`? | Dlaczego |
|--------|-----------------|----------|
| **A — interactive** (zalecana) | NIE | `setup_keyring.py --interactive` czyta klucze z prompta, idą prosto do Keychain. `.env` zbędny. |
| **B — bezpośrednio CLI `security`** | NIE | `security add-generic-password ...` zapisuje prosto do Keychain. `.env` zbędny. |
| **C — migracja z istniejącego `.env`** | TAK (tymczasowo) | `cp .env.example .env`, wpisujesz prawdziwe wartości, `setup_keyring.py` migruje do Keychain. Po migracji `.env` ma już tylko placeholdery. |

Realistycznie: jeśli zaczynasz od zera, użyj Metody A i `.env` zostawia się jako artefakt teoretyczny. Metoda C ma sens tylko gdy już masz `.env` z kluczami z poprzedniego projektu/setupu i chcesz to zmigrować.

### Co jeśli przypadkiem zacommituję `.env`?

`.gitignore` ten plik wyklucza, więc `git add .` go nie złapie. ALE — możesz strzelić sobie w stopę jeśli:

- Wymusisz `git add -f .env` (force)
- Zmodyfikujesz `.gitignore` żeby `.env` nie był ignorowany
- Skopiujesz prawdziwe wartości do `.env.example` przez pomyłkę

Jeśli to się stanie:

1. **Natychmiast zrotuj wszystkie klucze które wyciekły** (revoke w panelu providera + wygeneruj nowy + dodaj do Keychain)
2. **Nie próbuj usuwać commita force-pushem** — kopie zostają w cache GitHuba, forkach, reflogach. Klucz jest skompromitowany w momencie wycieku, nie naprawisz tego rewritem historii.
3. Patrz [docs/security-first.md](docs/security-first.md) → sekcja "Jeśli klucz i tak wycieknie" — pełna procedura.

## Walidacja cross-provider (bug którego nikt nie łapie za pierwszym razem)

Wyobraź sobie że przypadkiem trzymasz klucz OpenRouter pod etykietą `OPENAI_API_KEY`. Wysyłasz go do OpenAI. OpenAI zwraca `401 Unauthorized`. Spędzasz godzinę debugując swój kod.

Ten toolkit łapie to zanim request opuści maszynę:

```bash
python3 scripts/get_secret.py OPENAI_API_KEY
# →
# BŁĄD: OPENAI_API_KEY w Keychain wygląda jak klucz OpenRouter (zaczyna się od 'sk-or-').
# Najprawdopodobniej OPENROUTER_API_KEY został omyłkowo zapisany pod etykietą OPENAI_API_KEY.
# Naprawa:
#   1) Pobierz prawdziwy OPENAI_API_KEY: sk-proj-XXXX (z https://platform.openai.com/api-keys)
#   2) Nadpisz błędny wpis: ...
```

Działa out of the box dla OpenAI, Anthropic, OpenRouter, Google Gemini. Dodaj więcej w `scripts/get_secret.py` → `PROVIDER_FORMAT`. Patrz [docs/prefix-validation.md](docs/prefix-validation.md).

Wyłączenie na potrzeby testów: `python3 scripts/get_secret.py XYZ --no-validate`.

## Wzorzec wrappera MCP (dla użytkowników Claude Code / MCP)

Jeśli używasz Claude Code z serwerami MCP, na pewno trafiłeś na to — `.mcp.json` ma albo plaintext klucze w `env:` (źle — commituje się do git), albo nie ma kluczy w ogóle (i serwer MCP failuje).

Użyj zamiast tego wzorca wrappera shellowego. `scripts/mcp-wrapper-template.sh` to generyczny szablon; skopiuj i edytuj:

```bash
cp scripts/mcp-wrapper-template.sh scripts/mcp-mojserwer-wrapper.sh
# edytuj KEY_NAME i MCP_PACKAGE
chmod +x scripts/mcp-mojserwer-wrapper.sh
```

Następnie w `.mcp.json`:

```json
{
  "mcpServers": {
    "mojserwer": {
      "command": "/absolutna/sciezka/do/scripts/mcp-mojserwer-wrapper.sh"
    }
  }
}
```

Wrapper pobiera klucz z Keychain przy starcie, eksportuje go dla procesu MCP i `exec`'uje serwer. `.mcp.json` jest bezpieczny do commitowania — zawiera tylko ścieżkę.

Realny przykład: `examples/mcp-n8n-wrapper.sh` (wrapper dla n8n-mcp). Limitacje i serwery typu SSE pokryte w [docs/mcp-pattern.md](docs/mcp-pattern.md).

## Per-project services (opcjonalne)

Domyślnie klucze żyją pod nazwą serwisu Keychain `my-secrets`. Możesz nadpisać per-projekt:

```bash
# Jednorazowo:
KEYCHAIN_SERVICE=acme-prod python3 scripts/get_secret.py OPENAI_API_KEY

# Persystentnie (.zshrc albo per-project .envrc z direnv):
export KEYCHAIN_SERVICE="$(basename $(pwd))"
```

Różne serwisy trzymają klucze różnych projektów odseparowane. Ten sam Keychain, różne namespacy.

## Struktura

```
keychain-secrets-toolkit/
├── README.md                          # tu jesteś
├── LICENSE                            # MIT
├── .env.example                       # szablon (4 generyczne providery AI)
├── requirements.txt                   # keyring>=24.0
├── scripts/
│   ├── get_secret.py                  # główny lookup (Keychain → env → .env) + walidacja per-provider
│   ├── setup_keyring.py               # bulk migracja z .env, albo tryb --interactive
│   └── mcp-wrapper-template.sh        # generyczny wrapper MCP (skopiuj, edytuj KEY_NAME + MCP_PACKAGE)
├── examples/
│   ├── usage-curl.sh                  # curl z shell substitution
│   ├── usage-python.py                # subprocess + wzorzec SDK Pythona
│   └── mcp-n8n-wrapper.sh             # realny przykład wrappera (sanityzowany)
└── docs/
    ├── security-first.md              # PRZECZYTAJ PIERWSZE — gdzie klucze nigdy nie mogą trafić
    ├── lookup-chain.md                # jak get_secret.py znajduje Twoje klucze
    ├── prefix-validation.md           # ochrona przed cross-provider mismatch
    ├── mcp-pattern.md                 # wrappery MCP + limitacje SSE
    └── troubleshooting.md             # najczęstsze błędy i diagnostyka
```

## Czego tu NIE ma

- **Platformy inne niż macOS.** Biblioteka Pythona `keyring` działa na Windows/Linux, ale wywołania CLI `security` już nie. Skrypty musiałyby być zrefaktorowane żeby używać `keyring` ekskluzywnie. PR-y mile widziane.
- **Flow SSO / OAuth.** Tokeny OAuth wygasają — to nie są klucze API. Przechowywanie ich pod etykietami `_API_KEY` działa przez chwilę, potem failuje. Nie rób tego.
- **Setupy server-side / headless.** macOS Keychain wymaga odblokowanej sesji logowania. Dla headless serwerów użyj cloud secret managera (AWS Secrets Manager, GCP Secret Manager, Vault, etc.).
- **Sharing kluczy w zespole.** Ten toolkit jest single-user. Jeśli wiele osób potrzebuje tego samego klucza, użyj password managera z share'owaniem (1Password, Bitwarden) albo team secrets service.

## Licencja

MIT. Patrz [LICENSE](LICENSE).

## Kontrybucje

Issues i PR-y mile widziane — zwłaszcza:

- Wsparcie Windows / Linux (refactor żeby używać biblioteki `keyring` ekskluzywnie)
- Więcej prefixów providerów w `PROVIDER_FORMAT`
- Realne przykłady wrapperów MCP dla innych serwerów

Nie wrzucaj prawdziwych kluczy API do PR-ów, screenshotów ani przykładów. Używaj placeholderów typu `sk-proj-EXAMPLE-XXX`.
