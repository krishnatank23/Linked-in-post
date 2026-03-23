# LinkedIn Personal Branding Assistant (Agentic AI Backend)

Production-ready FastAPI backend implementing an 8-agent workflow for LinkedIn personal branding.

## Constraints Implemented

- No vector DB
- No embeddings
- LLM reasoning only (Groq API)
- Web search only (DuckDuckGo)

## Tech Stack

- FastAPI
- PostgreSQL + SQLAlchemy
- Groq Chat Completions API
- DuckDuckGo Search

## Project Structure

- `app/main.py` - app bootstrap + startup lifecycle
- `app/api/routes.py` - all API endpoints
- `app/db/models.py` - PostgreSQL data model
- `app/services/groq_client.py` - LLM integration with retry
- `app/services/duckduckgo_client.py` - search integration
- `app/services/parsers.py` - resume/LinkedIn parsing
- `app/agents/` - 8 modular agent implementations
- `app/orchestrator/analysis_service.py` - end-to-end workflow orchestration

## Endpoints

- `POST /register`
- `POST /upload-profile`
- `POST /run-analysis`
- `GET /influencers`
- `POST /select-influencers`
- `GET /gap-analysis`
- `POST /generate-strategy`
- `POST /generate-post`
- `GET /health`

## Setup

1. Create virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

```bash
copy .env.example .env
```

4. Update `.env` with valid values for `DATABASE_URL` and `GROQ_API_KEY`.

5. Run API:

```bash
uvicorn app.main:app --reload
```

## Notes

- Tables are auto-created at startup for quick bootstrapping.
- For production, add Alembic migrations and managed object storage for uploaded files.
- Tavily can replace DuckDuckGo later by adding another search client implementation.
