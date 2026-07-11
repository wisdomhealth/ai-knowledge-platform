# AI Knowledge Platform

Production-ready AI backend platform built with FastAPI, PostgreSQL, OpenAI, RAG,
Google Workspace APIs, web scraping, agent workflows, Twilio, and ElevenLabs.

This repository upgrades a Google Drive RAG backend into an enterprise-style AI
application that maps closely to the requested Upwork job: REST APIs, async
FastAPI, clean architecture, PostgreSQL schema design, Alembic migrations,
OpenAI-powered agents, tool execution, Google Sheets, web scraping, and voice AI.

## Upwork Match

Baseline match from the described current project: **58%**

Target match after the architecture upgrade in this repository: **96%**

The original system already covered FastAPI, REST APIs, Google Drive OAuth/API,
OpenAI embeddings, ChromaDB, semantic search, question answering over documents,
Docker/Git posture, and `.env` configuration. The upgrade adds the missing
production pieces: PostgreSQL, SQLAlchemy, Alembic, Google Sheets, scraping,
conversation and workflow agents, tool calling, persistent memory, Twilio,
ElevenLabs, stronger docs, and a GitHub-ready project layout.

Full comparison, roadmap, proposal, interview answers, and demo ideas are in:

- [Upwork alignment plan](docs/upwork_alignment.md)

## Architecture

```text
app/
  api/                 FastAPI routers, versioned endpoints, dependencies
  agents/              Conversation agent, workflow agent, tool registry, memory
  core/                Settings, database, logging
  integrations/        OpenAI, Google Drive, Google Sheets, scraper, voice vendors
  models/              SQLAlchemy ORM models
  rag/                 Chunking, embeddings, vector store, retrieval service
  repositories/        Database access layer
  schemas/             Pydantic request and response contracts
  services/            Business use cases
migrations/            Alembic environment and versioned migrations
docs/                  Upwork alignment, roadmap, proposal, demos
tests/                 API and service tests
```

## Core Capabilities

- Async FastAPI backend with versioned REST APIs.
- PostgreSQL persistence through SQLAlchemy 2.x async sessions.
- Alembic migrations for users, documents, chunks, conversations, messages,
  agent runs, tool executions, scraped pages, Sheets jobs, and voice sessions.
- OpenAI chat and embedding integration.
- Google Drive RAG ingestion and semantic search hooks.
- Google Sheets read and append integration.
- Async web scraper with HTML extraction and database persistence.
- Conversation Agent with memory and RAG context.
- Workflow Agent with deterministic multi-step tool execution.
- Tool registry for RAG search, web scraping, and Google Sheets operations.
- Voice Agent endpoints for Twilio webhooks and ElevenLabs synthesis.
- Environment-driven configuration suitable for local, staging, and production.

## Quick Start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`.

Containerized startup:

```bash
docker compose up --build
```

Interactive docs are available at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## API Surface

| Area | Method | Endpoint |
| --- | --- | --- |
| Health | `GET` | `/health` |
| Google Drive RAG | `POST` | `/api/v1/google-drive/sync` |
| Google Drive RAG | `POST` | `/api/v1/google-drive/search` |
| Google Drive RAG | `POST` | `/api/v1/google-drive/ask` |
| Google Sheets | `POST` | `/api/v1/google-sheets/read` |
| Google Sheets | `POST` | `/api/v1/google-sheets/append` |
| Web Scraper | `POST` | `/api/v1/scraper/scrape` |
| Agents | `POST` | `/api/v1/agents/conversation` |
| Agents | `POST` | `/api/v1/agents/workflow` |
| Voice | `POST` | `/api/v1/voice/twilio/inbound` |
| Voice | `POST` | `/api/v1/voice/synthesize` |

## Environment Variables

Required for a production deployment:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Optional integrations:

- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`
- `CHROMA_PERSIST_DIRECTORY`

## Database

The PostgreSQL schema is migration-managed by Alembic. The first migration
creates the production entities needed by the AI backend:

- `users`
- `documents`
- `document_chunks`
- `conversations`
- `messages`
- `agent_runs`
- `tool_executions`
- `sheet_sync_jobs`
- `scraped_pages`
- `voice_sessions`
- `integration_credentials`

Run migrations with:

```bash
alembic upgrade head
```

Create a new migration with:

```bash
alembic revision --autogenerate -m "describe change"
```

## Agent Design

The platform uses two agent layers:

- **Conversation Agent**: answers user questions using message history, memory,
  RAG context, and OpenAI chat completion.
- **Workflow Agent**: executes multi-step tool workflows using a registry of
  typed tools such as `rag.search`, `web.scrape`, `sheets.read`, and
  `sheets.append`.

Agent activity is persisted as `agent_runs` and `tool_executions`, which makes
workflow execution auditable and easy to debug.

## Production Notes

- Use PostgreSQL in all deployed environments.
- Store secrets in the deployment platform, not in `.env` files.
- Use separate Google OAuth credentials for development and production.
- Put the scraper behind rate limits and domain allowlists for client work.
- Enable Twilio request validation before public webhook exposure.
- Send structured logs to the deployment provider or an observability service.

## Upwork Positioning

This repository is designed to demonstrate exactly what the client asked for:
an AI backend that is not only a demo, but a clean, extensible platform. It can
support document RAG, Google Workspace workflows, autonomous tool execution,
web data ingestion, database-backed memory, and voice AI.
