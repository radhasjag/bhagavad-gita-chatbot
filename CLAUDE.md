# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Streamlit-based Bhagavad Gita chatbot that responds as Lord Krishna. Uses Azure OpenAI for generating responses based on relevant Gita verses found through text similarity matching.

## Commands

```bash
# Run the app
streamlit run main.py --server.port 5000

# Install dependencies (using uv)
uv sync

# Or with pip
pip install -r requirements.txt
```

## Required Environment Variables

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Deployment name for the model
- `LANGSMITH_API_KEY` - (optional) For LangSmith tracing

## Architecture

```
main.py                 → Streamlit UI, session management, conversation flow
gita_processor.py       → Verse matching using NLTK text similarity
response_generator.py   → Azure OpenAI API integration with retry logic
utils/
  monitoring.py         → EnhancedChatbotMonitor for metrics and logging
  production_utils.py   → Rate limiting, caching, session management
  text_processor.py     → NLTK preprocessing, Jaccard + semantic similarity
data/
  bhagavad_gita.csv     → Source data with columns: chapter, verse_number, verse_text, meaning
```

## Key Patterns

- **Response format**: Azure OpenAI returns structured responses with `short_answer` and `detailed_explanation` sections
- **Verse selection**: Combines text similarity scores with usage penalties (avoids repeating verses) and chapter diversity boosts
- **Session state**: Uses Streamlit's `st.session_state` for conversation history, verse tracking, and processing state
- **Caching**: TTLCache (1 hour) for API responses via `@cache_response` decorator
- **Monitoring**: Global `monitor` instance from `utils.monitoring` handles all logging and metrics
