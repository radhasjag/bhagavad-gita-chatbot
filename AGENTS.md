# AGENTS.md

This repository contains the live CrossRoads runtime.

## Working Context

- Canonical repo: `~/pro/srikrishnabot` on Radha's machine
- Public runtime: `https://crossroads.radhaj.com`
- Current hosting: AWS EC2 VM running Docker Compose and Caddy
- Current app shape: Streamlit frontend plus Python backend logic in the same repo
- Deploy ownership: Radha can keep doing local feature work; production deploys are currently a separate manual operator step

## Dependency Source Of Truth

- Use `requirements.txt` for actual runtime dependencies.
- Do not assume `pyproject.toml` or `uv.lock` match production. They are older artifacts and currently drift from the deployed stack.

## Local Development

Preferred setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run main.py
```

Required environment variables:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_VERSION` (optional, defaults to `2023-05-15`)

## Production Files

- `Dockerfile`
- `compose.prod.yml`
- `ops/Caddyfile`

Do not commit secrets. `.env` and `.env.prod` must remain untracked.

## Current Gotchas

- `response_generator.py` uses a direct Azure REST request for chat completions. Do not switch back to the older SDK helper unless the SDK/model/API-version combination is revalidated against the deployed Azure model.
- The mic button behavior in `main.py` must stay event-bound in JavaScript, not via inline HTML `onclick`.
- `gita_processor.py` relies on `st.session_state` for verse usage and chapter usage tracking.
- The old static shell and Replit-backed runtime are no longer the live production path. The EC2 + Compose stack is the current source of truth for deployment behavior.

## Git Hygiene

- Preserve changes in Radha's canonical repo on `radha-mac` when possible.
- Do not commit the screenshot PNG files in the repo root.
- If you update repo-local agent guidance, keep `README.md`, `AGENTS.md`, and `CLAUDE.md` aligned.
