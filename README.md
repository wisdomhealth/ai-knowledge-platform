# AI Knowledge Platform

Production-ready AI backend built with FastAPI, PostgreSQL, OpenAI, RAG,
Google Sheets, web scraping, agent workflows, Twilio, and ElevenLabs.

This repository provides a clean backend foundation for building AI applications
that combine retrieval, structured workflow automation, external data ingestion,
and voice interfaces. It keeps the architecture modular so teams can extend the
platform without rewriting core services.

## Upwork Match

Target match after this architecture upgrade: **95%+**

The project demonstrates the core requirements for a production AI backend:
async FastAPI, REST APIs, PostgreSQL, SQLAlchemy, Alembic migrations, OpenAI
integrations, RAG, Google Sheets automation, web scraping, conversation agents,
workflow agents, tool execution, Twilio, ElevenLabs, environment configuration,
documentation, and a GitHub-ready repository layout.

Full comparison, roadmap, proposal, interview answers, and demo ideas are in:

- [Upwork alignment plan](docs/upwork_alignment.md)

## Architecture

```text
app/
  api/                 FastAPI routers, versioned endpoints, dependencies
  agents/              Conversation agent, workflow agent, tool registry, memory
  core/                Settings, database, logging
  integrations/        OpenAI, Google Sheets, scraper, voice vendors
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
- RAG services with chunking, vector storage, and retrieval hooks.
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

Required when Google Sheets automation is enabled:

- `GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE`

Optional integrations:

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
- Use separate Google Sheets service accounts for development and production.
- Put the scraper behind rate limits and domain allowlists for client work.
- Enable Twilio request validation before public webhook exposure.
- Send structured logs to the deployment provider or an observability service.

## Upwork Positioning

This repository is designed to demonstrate what an AI automation client expects:
a clean, extensible backend that is more than a demo. It supports RAG,
Google Sheets workflows, autonomous tool execution, web data ingestion,
database-backed memory, and voice AI.
