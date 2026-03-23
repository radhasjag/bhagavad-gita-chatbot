# CrossRoads

CrossRoads is a Streamlit-based Bhagavad Gita guidance app that responds in the voice of Lord Krishna. It finds relevant verses from the Gita and uses Azure OpenAI to generate a short answer plus a more detailed explanation for modern life decisions.

## Current Status

- Live runtime: `https://crossroads.radhaj.com`
- Hosting: single AWS EC2 VM running Docker Compose with Caddy
- Development model: local-first on Radha's machine, with deploys run as a separate manual operator workflow
- Frontend shape: still Streamlit, not a Next.js app

## Repository Layout

```text
main.py                 Streamlit UI, conversation flow, voice button wiring
gita_processor.py       Verse selection, diversity scoring, session-state usage tracking
response_generator.py   Azure OpenAI request path and response parsing
utils/                  Monitoring, caching, session helpers, text preprocessing
data/                   Bhagavad Gita verse dataset
Dockerfile              Production app image
compose.prod.yml        Production app + Caddy stack
ops/Caddyfile           HTTPS reverse-proxy config for crossroads.radhaj.com
```

## Local Development

Use `requirements.txt` as the dependency source of truth.

`pyproject.toml` and `uv.lock` are older Replit-era artifacts and do not currently match the production runtime dependency pins. Do not assume `uv sync` reproduces production until those files are reconciled.

### Prerequisites

- Python 3.11
- Azure OpenAI credentials

### Required Environment Variables

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_VERSION` (optional, defaults to `2023-05-15`)
- `LANGSMITH_API_KEY` (optional)

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Locally

```bash
streamlit run main.py
```

## Production Deployment

Production uses:

- `Dockerfile` for the app image
- `compose.prod.yml` for the app and reverse proxy
- `ops/Caddyfile` for HTTPS and hostname routing

Secrets stay out of git. Local development uses `.env`; production uses `.env.prod` on the server.

Current deploy flow is intentionally manual:

1. Make and validate changes locally.
2. Sync the repo to the production VM.
3. Update `.env.prod` on the VM if needed.
4. Rebuild and restart with `docker compose -f compose.prod.yml up -d --build`.

## Important Implementation Notes

- `response_generator.py` currently uses a direct Azure REST call for chat completions instead of relying on the older Python SDK request helper. This was required because the deployed model expects `max_completion_tokens`, while the older SDK path in this repo did not handle that combination correctly.
- The voice UI is injected from `main.py`. Do not reintroduce inline `onclick` handlers into the mic button markup; Streamlit's frontend stack can break on that pattern.
- `gita_processor.py` depends on Streamlit session state for verse usage tracking. Standalone scripts that import it should either initialize session state or avoid expecting full app behavior.

## Versioning Notes

- Screenshot captures in the repo root are local artifacts and are intentionally ignored.
- The deploy stack and current runtime fixes were preserved in local commits on Radha's machine before new voice work begins.
