#!/bin/bash
# Przykład: użycie get_secret.py z curl poprzez podstawienie powłoki (shell substitution).
#
# Klucz jest rozwiązywany wewnątrz $(...) przez powłokę i wstawiany do argumentów
# curl. Nigdy nie pojawia się na stdout — curl widzi ciało żądania, a ty
# widzisz odpowiedź API.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GET_SECRET="python3 $REPO_ROOT/scripts/get_secret.py"

# Przykład 1: OpenAI chat completion
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $($GET_SECRET OPENAI_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'

# Przykład 2: Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $($GET_SECRET ANTHROPIC_API_KEY)" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":100,"messages":[{"role":"user","content":"hi"}]}'

# Przykład 3: OpenRouter (z opcjonalnym --no-validate dla kluczy innych niż AI)
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $($GET_SECRET OPENROUTER_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemini-2.5-pro","messages":[{"role":"user","content":"hi"}]}'
