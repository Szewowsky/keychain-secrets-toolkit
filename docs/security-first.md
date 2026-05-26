# Security First — Gdzie klucze nigdy nie mogą trafić

Przeczytaj to, **zanim** skopiujesz gdziekolwiek jakikolwiek klucz. To najważniejsza strona w tym zestawie narzędzi.

## Jedyna zasada

> **Klucze żyją w macOS Keychain. Nigdy nie trafiają nigdzie indziej.**

Nigdzie indziej oznacza: czaty AI, wiadomości commitów, historię shella, zrzuty ekranu, screencasty, wiadomości prywatne na Slacku, karteczki na Twoim monitorze, zwykłe pliki `.env` zacommitowane do gita. Wszystko to stanowi wektor wycieku.

## Nigdy nie wklejaj kluczy do czatów AI

Claude Code, ChatGPT, Cursor, Gemini, Copilot Chat i wszystkie inne — **nigdy nie wklejaj do nich kluczy API.**

Kiedy wklejasz klucz do narzędzia AI:

- Trafia on do **kontekstu sesji**, który widzi model. Model technicznie "zna" go przez resztę tej sesji.
- Jest przetwarzany przez **potok dostawcy** (Anthropic, OpenAI, itp.). Renomowani dostawcy deklarują, że nie trenują na tych danych, ale dane te są nadal widoczne dla ich systemów inferencyjnych i przechowywane w logach przez okres retencji określony w ich regulaminach.
- Zostaje w **transkrypcie Twojej konwersacji**. Jeśli kiedykolwiek wyeksportujesz, udostępnisz lub zrobisz zrzut ekranu tej rozmowy — klucz wycieknie.
- Przyszły błąd w narzędziu AI (logowanie ewaluacji, eskalacja wsparcia, snapshot debugowania) może ujawnić ten transkrypt ludziom po stronie dostawcy.

Jeśli kiedykolwiek przypadkowo wkleisz klucz — **natychmiast go zrotuj** (unieważnij w UI dostawcy, wygeneruj nowy). Nie próbuj usuwać historii czatu i liczyć na cud. Zakładaj, że klucz został skompromitowany.

## Nigdy nie umieszczaj kluczy w wiadomościach commitów ani poleceniach

```bash
# ŹLE — wycieka do historii gita na zawsze:
git commit -m "fix auth; using OPENAI_API_KEY=sk-proj-abc123..."

# ŹLE — wycieka do ~/.zsh_history:
OPENAI_API_KEY=sk-proj-abc123... node app.js
```

Oba te przypadki są do odzyskania. `git log --all -p` znajdzie ten pierwszy nawet po force-pushu (osierocone commity pozostają osiągalne przez reflog i packfiles). `~/.zsh_history` to zwykły tekst (plaintext).

## Bezpieczne dodawanie kluczy — trzy sposoby

Wybierz najbezpieczniejszy, na jaki pozwala Twoja sytuacja.

### 1. Interaktywny Python (zalecane — brak historii shella)

```bash
python3 -c "import keyring; keyring.set_password('my-secrets', 'OPENAI_API_KEY', input('Key: '))"
```

Wpisujesz klucz w prompcie. Nigdy nie trafia on do `~/.zsh_history`, nigdy nie trafia do pliku, idzie prosto z Twoich palców do Keychain.

### 2. Natywne CLI `security` w macOS

```bash
security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w 'sk-proj-XXX'
```

W tym przypadku klucz **znajduje się** w historii Twojego shella — `~/.zsh_history` zapisze całe polecenie. Jeśli musisz tego użyć, poprzedź polecenie spacją (jeśli masz ustawione `HIST_IGNORE_SPACE` w zsh) lub wyczyść historię po wszystkim:

```bash
history -d $(history | tail -1 | awk '{print $1}')
```

### 3. Masowa migracja z `.env`

```bash
python3 scripts/setup_keyring.py
```

Odczytuje Twój istniejący `.env`, przenosi wartości do Keychain, nadpisuje `.env` placeholderami `STORED_IN_KEYRING`. Użyj tego **raz** podczas migracji z niebezpiecznej konfiguracji. Nie wracaj później do `.env`.

## Nigdy nie przechowuj kluczy na zrzutach ekranu ani screencastach

Jeśli nagrywasz swój terminal:

- Najpierw wyczyść scrollback: `clear && printf '\e[3J'`
- Nie uruchamiaj `env` ani `printenv` podczas nagrywania
- Nie rozwijaj podstawień `$(...)` przed kamerą — wynik zostaje w buforze przewijania

Częsty wyciek: pokazywanie `.zshrc` lub historii poleceń podczas tutoriala.

## Nigdy nie commituj `.env`

```bash
# .gitignore musi zawierać:
.env
.env.local
.env.*.local
*.key
*.pem
credentials.json
.mcp.json
```

Znajduje się to już w `.gitignore` tego repozytorium. Jeśli kopiujesz ten zestaw narzędzi do innego projektu, **skopiuj również `.gitignore`** lub scal te linie z już istniejącym plikiem.

> Pełne wytłumaczenie patternu `.env.example` vs `.env` (kiedy potrzebujesz lokalnego `.env`, co oznacza `STORED_IN_KEYRING`, kiedy w ogóle pomijasz `.env`) — patrz README sekcja [Dlaczego dwa pliki](../README.md#dlaczego-dwa-pliki-envexample-vs-env).

## Jeśli klucz i tak wycieknie

1. **Natychmiast go zrotuj.** Unieważnij w UI dostawcy, wygeneruj nowy klucz, dodaj go do Keychain.
2. **Nie próbuj przepisywać historii gita.** Force-push nadpisujący commit z wyciekiem nie pomaga — cache, forki i log zdarzeń GitHub zachowują kopie. Klucz jest skompromitowany; jedynym rozwiązaniem jest rotacja.
3. **Sprawdź logi audytowe dostawcy.** OpenAI, Anthropic itp. mają panele zużycia. Szukaj aktywności z adresów IP, które nie należą do Ciebie.

## Dlaczego ma to większe znaczenie, niż myślisz

Domyślnym wektorem wycieku kluczy API do AI w 2026 roku nie jest ktoś włamujący się na Twoją maszynę. Jest nim:

- Plik `.env`, o którym zapomniałeś, że został zacommitowany
- Zrzut ekranu na publicznym kanale Slack
- Klucz wklejony do ChatGPT w celu "debugowania"
- `git log` udostępniony podczas code review

Ten zestaw narzędzi istnieje, ponieważ **wygoda jest wrogiem bezpieczeństwa**. Keychain nie jest najszybszą konfiguracją. Jest tą, która nie przecieka.
