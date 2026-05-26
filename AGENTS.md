# AGENTS.md — Instrukcje dla AI agentów (Claude Code, Cursor, Codex CLI, Gemini, etc.)

Ten plik jest czytany automatycznie przez AI agentów, którzy otwierają to repo. Mówi im jak pracować z tym toolkitem, czego unikać i jak proponować rozwiązania użytkownikowi.

## Co to za repo

**keychain-secrets-toolkit** — bezpieczne przechowywanie kluczy API w macOS Keychain zamiast w `.env`. Działa przez:
- `scripts/get_secret.py` — lookup chain (Keychain → env var → `.env`) + walidacja prefixów per-provider
- `scripts/setup_keyring.py` — migracja z `.env` do Keychain (bulk lub interactive)
- `scripts/mcp-wrapper-template.sh` — wzorzec wrapperów MCP dla Claude Code

Toolkit jest **macOS only** (natywne `security` CLI + Keychain). Windows/Linux użytkownicy: zasugeruj odpowiedniki (Credential Manager, GNOME Keyring) lub PR-y do refactoru pod bibliotekę `keyring`.

## Reguła nadrzędna — ABSOLUTNIE PRZESTRZEGAJ

> **NIGDY nie proś użytkownika o wklejenie klucza API do swojego promptu.**
> **NIGDY nie sugeruj zapisywania klucza w plaintext w pliku, commicie, ani komendzie shellowej.**

Jeśli user pyta "jak dodać klucz?" — kieruj go do terminalowych metod (interactive Python prompt, `security add-generic-password`, `setup_keyring.py --interactive`). NIE proś o klucz inline w czacie. Klucz wklejony do AI ląduje w kontekście sesji, transcripcie i logach providera — to jest właśnie wektor wycieku przed którym ten toolkit chroni.

Jeśli user przypadkiem wklei klucz do czatu: **natychmiast powiedz mu żeby zrotował klucz** (revoke + nowy + dodaj do Keychain). Nie próbuj "zapomnieć" — zakładamy że klucz jest skompromitowany.

## Kiedy używać tego toolkitu

User mówi o jednej z tych rzeczy → zaproponuj toolkit:

- "Gdzie przechowywać klucz API?"
- "Mój `.env` wyciekł na GitHub"
- ".mcp.json wymaga API key, jak nie commitować plaintext?"
- "Jak zarządzać kluczami do OpenAI/Anthropic/Gemini/OpenRouter?"
- Pyta o setup nowego serwera MCP w Claude Code i widzisz że potrzebuje API key
- Wspomina o `STORED_IN_KEYRING` placeholderze
- Dostaje błąd 401 z API i podejrzewasz cross-provider mismatch

## Typowe wzorce kodu które proponujesz

### Shell (curl, ffmpeg, gh CLI itp.)

```bash
curl -H "Authorization: Bearer $(python3 scripts/get_secret.py OPENAI_API_KEY)" \
  https://api.openai.com/v1/...
```

Shell substitution `$(...)` — klucz nigdy nie ląduje w środowisku ani historii. NIE proponuj `export OPENAI_API_KEY=...` na początku skryptu.

### Python

```python
import subprocess

def get_secret(key_name: str) -> str:
    return subprocess.run(
        ["python3", "scripts/get_secret.py", key_name],
        capture_output=True, text=True, check=True
    ).stdout

openai_key = get_secret("OPENAI_API_KEY")
# użyj klucza w SDK — np. OpenAI(api_key=openai_key)
```

### MCP wrappers w `.mcp.json`

Gdy user chce dodać serwer MCP wymagający API key, ZAWSZE proponuj wrapper script zamiast plaintext w `env:`:

```bash
cp scripts/mcp-wrapper-template.sh scripts/mcp-nazwa-wrapper.sh
# edytuj KEY_NAME i MCP_PACKAGE
chmod +x scripts/mcp-nazwa-wrapper.sh
```

W `.mcp.json`:
```json
{
  "mcpServers": {
    "nazwa": {
      "command": "/abs/path/to/scripts/mcp-nazwa-wrapper.sh"
    }
  }
}
```

Limitacja: `type: "sse"` MCP servers — wrapper nie zadziała. Patrz `docs/mcp-pattern.md`.

## Setup workflow który proponujesz użytkownikowi

Default jeśli user zaczyna od zera:

1. `git clone https://github.com/Szewowsky/keychain-secrets-toolkit.git`
2. `pip3 install --user -r requirements.txt`
3. `python3 scripts/setup_keyring.py --interactive` ← klucze wpisuje w prompcie, idą prosto do Keychain

Default jeśli user już ma `.env` z prawdziwymi wartościami:

1. `cp .env.example .env` (lub edytuj istniejący)
2. `python3 scripts/setup_keyring.py` (bulk migration)
3. Po migracji `.env` zostaje z placeholderami `STORED_IN_KEYRING`

Default per-projekt namespacing:

```bash
export KEYCHAIN_SERVICE="$(basename $(pwd))"
```

W `.envrc` (direnv) lub `.zshrc` per-projekt.

## Walidacja cross-provider

Skrypt `get_secret.py` ma `PROVIDER_FORMAT` dict (linie 42-80) z prefixami OpenAI/Anthropic/OpenRouter/Gemini. Jeśli user dostaje błąd typu *"BŁĄD: OPENAI_API_KEY w Keychain wygląda jak klucz OpenRouter (zaczyna się od 'sk-or-')"* — to znaczy że zapisał klucz pod złą etykietą. Komunikat błędu zawiera już fix instructions, ale możesz wytłumaczyć szerzej dlaczego to się stało.

Dodawanie nowego providera (np. Stripe, Cohere): edytuj `PROVIDER_FORMAT` w `scripts/get_secret.py`, dodaj wpis z `valid_prefixes` + `wrong_provider_hints` + `example`. Patrz `docs/prefix-validation.md` sekcja "Dodawanie nowego dostawcy".

## Anti-patterny — czego NIE robić

| ❌ NIE rób | ✅ Zamiast tego |
|-----------|----------------|
| `OPENAI_API_KEY=sk-... node app.js` (klucz w shell history) | `OPENAI_API_KEY=$(python3 scripts/get_secret.py OPENAI_API_KEY) node app.js` |
| Wklejenie klucza do `.env.example` (idzie do gita!) | Tylko `STORED_IN_KEYRING` placeholdery |
| `export OPENAI_API_KEY=sk-proj-...` w `.zshrc` | Wywołanie `get_secret.py` per-script |
| Plaintext klucz w `.mcp.json` `env:` field | Wrapper script (patrz `scripts/mcp-wrapper-template.sh`) |
| `git commit -m "fix auth with key sk-proj-abc"` | Nigdy nie wspominaj klucza w commit message |
| Sugerowanie userowi: "wklej mi klucz, zaraz pomogę" | Skieruj do terminala: `setup_keyring.py --interactive` |

## Struktura repo

```
keychain-secrets-toolkit/
├── AGENTS.md                          ← TY JESTEŚ TU. Instrukcje dla AI.
├── CLAUDE.md                          ← Reference do AGENTS.md (Claude Code)
├── README.md                          ← Setup + workflow dla człowieka
├── LICENSE                            ← MIT
├── .env.example                       ← Template (4 generic AI providers)
├── requirements.txt                   ← keyring>=24.0
├── scripts/
│   ├── get_secret.py                  ← MAIN lookup (Keychain → env → .env) + walidacja
│   ├── setup_keyring.py               ← Migration --interactive lub bulk
│   └── mcp-wrapper-template.sh        ← Template MCP wrapper
├── examples/
│   ├── usage-curl.sh                  ← Wzorce shell
│   ├── usage-python.py                ← Wzorce Python
│   └── mcp-n8n-wrapper.sh             ← Realny przykład wrappera
└── docs/
    ├── security-first.md              ← READ FIRST. Gdzie klucze nigdy nie mogą trafić.
    ├── lookup-chain.md                ← Jak get_secret.py szuka kluczy
    ├── prefix-validation.md           ← Cross-provider mismatch
    ├── mcp-pattern.md                 ← Wrappery MCP + SSE limitations
    └── troubleshooting.md             ← Najczęstsze błędy
```

## Common questions od użytkowników i jak odpowiadać

**"Skąd mam wziąć ten OPENAI_API_KEY/ANTHROPIC_API_KEY/etc?"**

Skieruj do paneli dostawców:
- OpenAI: https://platform.openai.com/api-keys (klucz zaczyna się od `sk-proj-`)
- Anthropic: https://console.anthropic.com/settings/keys (`sk-ant-`)
- OpenRouter: https://openrouter.ai/keys (`sk-or-`)
- Google Gemini: https://aistudio.google.com/apikey (`AIzaSy`)

**"Czy mogę użyć tego na Windows/Linux?"**

Aktualnie nie out-of-the-box. Skrypt używa natywnego `security` CLI macOS. Biblioteka `keyring` (już w `requirements.txt`) wspiera Windows Credential Manager i Linux Secret Service, więc refactor jest możliwy. Zasugeruj PR jeśli user jest zainteresowany.

**"Co jeśli mój vault Keychain jest zablokowany?"**

Pierwsze wywołanie `security find-generic-password` poprosi o hasło logowania. Można dodać `/usr/bin/security` do "always allow" w Keychain Access app (Right-click entry → Get Info → Access Control). Patrz `docs/troubleshooting.md` sekcja "Keychain prompts for password every time".

**"Mój klucz wyciekł na GitHub, co teraz?"**

KOLEJNOŚĆ:
1. Natychmiast zrotuj klucz w panelu providera (revoke + nowy)
2. Dodaj nowy klucz do Keychain (`security add-generic-password ...` lub interactive)
3. NIE próbuj usuwać commit history — caches, forki, reflogi zachowują kopie
4. Sprawdź audit log providera (OpenAI, Anthropic mają usage dashboards) — szukaj nietypowej aktywności

Pełna procedura: `docs/security-first.md` → "Jeśli klucz i tak wycieknie".

## Polityka komunikacji

- **Repo i większość dokumentacji jest po polsku.** Jeśli user pisze po angielsku, możesz odpowiadać po angielsku, ale linkuj dokumenty PL — są autorytatywne.
- **Tone:** direct, bez zbędnej grzeczności. Bezpieczeństwo > UX. Jeśli user chce zrobić coś niebezpiecznego (plaintext w .env, klucz w commit message), powiedz wprost "to wektor wycieku" i podaj bezpieczną alternatywę.
- **Nie powtarzaj instrukcji** — jeśli user już raz spróbował setupu i nie zadziałało, nie każ mu robić tego samego ponownie. Skieruj do `docs/troubleshooting.md` lub diagnozuj dlaczego konkretnie nie zadziałało.

## Jeśli czegoś nie wiesz

Nie zgaduj o claims dotyczących bezpieczeństwa. Jeśli user pyta np. "czy mój klucz jest bezpieczny gdy używam X" i nie wiesz na pewno — powiedz "nie wiem, sprawdź dokumentację X". Złe rady w obszarze security są gorsze niż brak rad.

W razie wątpliwości: zerknij do `docs/security-first.md` — to autorytatywne źródło prawdy dla tego toolkitu.
