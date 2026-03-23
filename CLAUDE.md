# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

A Streamlit-based Bhagavad Gita chatbot that responds as Lord Krishna. It is live at `https://crossroads.radhaj.com` on a single AWS EC2 VM using Docker Compose and Caddy.

This repo remains a Streamlit app. It has not been migrated to Next.js.

## Commands

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app locally
streamlit run main.py

# Production deploy on the server
docker compose -f compose.prod.yml up -d --build
```

`requirements.txt` is the runtime dependency source of truth.

`pyproject.toml` and `uv.lock` are older Replit-era artifacts and do not currently match the deployed runtime dependency pins.

## Required Environment Variables

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Deployment name for the model
- `AZURE_OPENAI_API_VERSION` - Optional, defaults to `2023-05-15`
- `LANGSMITH_API_KEY` - Optional LangSmith tracing key

## Architecture

```text
main.py                 Streamlit UI, session management, conversation flow
gita_processor.py       Verse matching using NLTK text similarity
response_generator.py   Azure OpenAI request path and response parsing
utils/
  monitoring.py         Metrics and logging
  production_utils.py   Rate limiting, caching, session management
  text_processor.py     NLTK preprocessing, Jaccard + semantic similarity
data/
  bhagavad_gita.csv     Verse source data
Dockerfile              Production app image
compose.prod.yml        Production app + Caddy stack
ops/Caddyfile           HTTPS reverse-proxy config
```

## Key Patterns

- **Response format**: The app expects `short_answer` and `detailed_explanation`
- **Verse selection**: Similarity scoring plus usage penalties and chapter diversity boosts
- **Session state**: Uses `st.session_state` for conversation history and verse tracking
- **Caching**: TTLCache-based response caching via `@cache_response`
- **Monitoring**: Global `monitor` instance from `utils.monitoring`
- **Current Azure request path**: `response_generator.py` uses a direct Azure REST call for chat completions to avoid the older SDK/model parameter mismatch
- **Voice UI constraint**: The microphone button in `main.py` must not use inline HTML `onclick` attributes

## Production Context

- The live runtime is the EC2-hosted Docker Compose stack, not the earlier static shell or Replit runtime
- `Dockerfile`, `compose.prod.yml`, and `ops/Caddyfile` are part of the production path
- `.env.prod` is server-only and must not be committed

## Repo Hygiene

- Screenshot PNG files in the repo root are local artifacts and should stay out of git
- Keep `README.md`, `AGENTS.md`, and `CLAUDE.md` aligned when repo workflow or deployment assumptions change
