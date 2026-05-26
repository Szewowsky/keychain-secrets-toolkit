#!/bin/bash
# Example: using get_secret.py with curl via shell substitution.
#
# The key is resolved inside $(...) by the shell and inlined into curl's
# arguments. It never appears on stdout — curl sees the request body, you
# see the API response.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GET_SECRET="python3 $REPO_ROOT/scripts/get_secret.py"

# Example 1: OpenAI chat completion
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $($GET_SECRET OPENAI_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'

# Example 2: Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $($GET_SECRET ANTHROPIC_API_KEY)" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":100,"messages":[{"role":"user","content":"hi"}]}'

# Example 3: OpenRouter (with optional --no-validate for non-AI keys)
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $($GET_SECRET OPENROUTER_API_KEY)" \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemini-2.5-pro","messages":[{"role":"user","content":"hi"}]}'
