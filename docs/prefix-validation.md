# Walidacja prefiksów — wyłapywanie niezgodności między dostawcami

Dziwny błąd z prawdziwego życia: prosisz o `OPENAI_API_KEY`, otrzymujesz wartość, wysyłasz ją do OpenAI, a API zwraca ogólne `401 Unauthorized`. Po godzinie debugowania swojego kodu uświadamiasz sobie, że wartość zapisana pod `OPENAI_API_KEY` była tak naprawdę Twoim kluczem OpenRouter, błędnie nazwanym.

To właśnie ten błąd wyłapuje walidacja prefiksów. Zanim `get_secret.py` zwróci wartość, sprawdza prefiks, aby upewnić się, że pasuje on do tego, jak faktycznie wyglądają klucze danego dostawcy.

## Prefiksy dostawców

| Dostawca | Prefiks(y) klucza | Skąd pobrać |
|----------|----------------|--------------|
| OpenAI | `sk-proj-`, `sk-svcacct-`, `sk-` | https://platform.openai.com/api-keys |
| Anthropic | `sk-ant-` | https://console.anthropic.com/settings/keys |
| OpenRouter | `sk-or-` | https://openrouter.ai/keys |
| Google Gemini | `AIzaSy` | https://aistudio.google.com/apikey |

Są one stabilne, udokumentowane i pozostają niezmienne od lat. Walidacja to po prostu sprawdzenie za pomocą `startswith()`.

## Co robi walidacja

Kiedy wywołujesz `get_secret.py OPENAI_API_KEY`:

1. Pobiera wartość z Keychain (lub env/`.env`)
2. Sprawdza: czy wartość zaczyna się od `sk-proj-`, `sk-svcacct-` lub `sk-`?
3. Jeśli tak → zwraca wartość
4. Jeśli nie → sprawdza, czy zaczyna się od prefiksu innego znanego dostawcy (`sk-or-`, `sk-ant-`, `AIzaSy` itp.)
5. Jeśli tak → przerywa działanie z komunikatem w stylu: *"BŁĄD: OPENAI_API_KEY w Keychain wygląda jak klucz OpenRouter (zaczyna się od `sk-or-`). Najprawdopodobniej OPENROUTER_API_KEY został omyłkowo zapisany pod etykietą OPENAI_API_KEY. Naprawa: ..."*
6. Jeśli żaden znany prefiks nie pasuje → przerywa działanie z komunikatem: *"BŁĄD: OPENAI_API_KEY ma nieznany format (zaczyna się od `abc12345...`). Oczekiwany format: sk-proj-XXXX"*

## Przykład: wyłapanie błędu

```bash
# Przypadkowe zapisanie klucza OpenRouter pod etykietą OpenAI:
security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w 'sk-or-v1-real-openrouter-key'

# Próba użycia:
python3 scripts/get_secret.py OPENAI_API_KEY
# →
# BŁĄD: OPENAI_API_KEY w Keychain wygląda jak klucz OpenRouter (zaczyna się od 'sk-or-').
# Najprawdopodobniej OPENROUTER_API_KEY został omyłkowo zapisany pod etykietą OPENAI_API_KEY.
# Naprawa:
#   1) Pobierz prawdziwy OPENAI_API_KEY: sk-proj-XXXX (z https://platform.openai.com/api-keys)
#   2) Nadpisz błędny wpis:
#      security add-generic-password -U -a OPENAI_API_KEY -s my-secrets -w '<your-key>'
#   3) Zweryfikuj: python3 scripts/get_secret.py OPENAI_API_KEY | head -c 12
```

Rozwiązanie znajduje się bezpośrednio w komunikacie o błędzie. Żadnych zapytań do API, żadnego `401`, żadnego debugowania Twojego kodu.

## Dlaczego ma to znaczenie w praktyce

Kiedy żonglujesz 4-5 dostawcami AI, ten błąd **na pewno** się zdarzy. Prawdziwe scenariusze:

- Wklejasz klucz z panelu dostawcy do polecenia `security add-generic-password`, ale przypadkowo zamieniasz miejscami wartości dwóch argumentów
- Członek zespołu dodaje klucz pod złą etykietą we współdzielonej dokumentacji
- Rotujesz klucz jednego z dostawców i kopiujesz go w złe miejsce
- Skrypt migracyjny (w tym `setup_keyring.py`) czyta linie z `.env`, a jeden z wierszy zawierał literówkę

Bez walidacji prefiksów spędzasz godzinę na debugowaniu swojego kodu, podczas gdy dostawca wciąż zwraca `401`. Z nią widzisz rzeczywisty problem już przy następnym poleceniu.

## Wyłączanie walidacji

Dla kluczy spoza `PROVIDER_FORMAT` (np. `STRIPE_API_KEY`, `INTERNAL_TOKEN`, cokolwiek niestandardowego), walidacja jest pomijana automatycznie — nie ma specyfikacji, do której można by je dopasować.

Dla znanych dostawców, jeśli masz powód, by ją pominąć (testowanie, migracja), przekaż `--no-validate`:

```bash
python3 scripts/get_secret.py OPENAI_API_KEY --no-validate
```

Zwraca to cokolwiek jest zapisane, bez żadnych sprawdzeń. Nie używaj tego w kodzie produkcyjnym — mija się to z celem.

## Dodawanie nowego dostawcy

Edytuj `PROVIDER_FORMAT` w `scripts/get_secret.py`:

```python
"NEW_PROVIDER_KEY": {
    "valid_prefixes": ("nv-",),                          # od czego zaczynają się prawidłowe klucze
    "wrong_provider_hints": {                            # inne prefiksy → zasugeruj właściwą etykietę
        "sk-proj-": ("OPENAI_API_KEY", "OpenAI project key"),
        "sk-or-":   ("OPENROUTER_API_KEY", "OpenRouter"),
    },
    "example": "nv-XXXX (from https://newprovider.example.com/keys)",
},
```

Wzorzec jest następujący: wylistuj prawidłowe prefiksy dla etykiety tego klucza, a następnie wylistuj prefiksy innych dostawców, które chcesz wyłapywać (aby błąd mógł zasugerować właściwą etykietę).
