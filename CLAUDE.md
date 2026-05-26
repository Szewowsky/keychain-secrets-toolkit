# CLAUDE.md

Główne instrukcje dla Claude Code w tym repo znajdują się w [AGENTS.md](AGENTS.md).

## Quick reference (Claude-specific)

Ten plik istnieje żeby Claude Code automatycznie wczytał kontekst projektu. Wszystkie reguły są w AGENTS.md — przeczytaj go w pierwszej kolejności.

**Najważniejsza reguła:** NIGDY nie proś użytkownika o wklejenie klucza API do czatu. Klucze dodaje się tylko w terminalu, przez `setup_keyring.py --interactive` lub `security add-generic-password`. Pełne wytłumaczenie w `AGENTS.md` sekcja "Reguła nadrzędna".

**Główne pliki:**
- `scripts/get_secret.py` — lookup z Keychain
- `scripts/setup_keyring.py` — migracja kluczy z `.env`
- `scripts/mcp-wrapper-template.sh` — wzorzec wrappera MCP dla `.mcp.json`

**Dla pełnego kontekstu projektu, sub-agentów i wzorców użycia:** [@AGENTS.md](AGENTS.md)
