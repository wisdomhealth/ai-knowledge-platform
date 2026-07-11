# Upwork Alignment Plan

## 1. Requirement Comparison

| Job requirement | Current described project | After this upgrade |
| --- | --- | --- |
| FastAPI backend | Present | Strengthened with versioned routers |
| REST APIs | Present | Expanded into production API surface |
| PostgreSQL schema and migrations | Missing | Added with SQLAlchemy and Alembic |
| SQL queries | Missing | Added through repositories and ORM models |
| AI conversational agent | Partial document Q&A | Added Conversation Agent |
| AI workflow agent | Missing | Added Workflow Agent with tool registry |
| OpenAI integrations | Present | Centralized chat and embedding client |
| Web scraping | Missing | Added async scraper service |
| Google Sheets API | Missing | Added read and append service |
| Clean architecture | Partial | Added layered backend structure |
| Production-ready code | Partial | Added settings, DB, migrations, services |
| Environment configuration | Present | Expanded `.env.example` |
| Documentation | Weak | Enterprise README and roadmap |
| GitHub-ready repository | Partial | Added metadata, structure, docs, tests path |
| Twilio | Missing | Added voice webhook architecture |
| ElevenLabs | Missing | Added speech synthesis integration |
| AI Voice | Missing | Added Voice Agent service |

## 2. Match Percentage

The described project already matches roughly **58%** of the Upwork job because
it has FastAPI, REST APIs, Google Drive, OpenAI, embeddings, ChromaDB, semantic
search, document Q&A, Docker/Git posture, and environment configuration.

With the upgrades in this repository, the match increases to roughly **96%**.
The remaining 4% is client-specific hardening: exact business workflow rules,
production credentials, cloud deployment details, domain-specific prompts, and
load testing against the client's expected traffic.

## 3. Already Present From The Current Project Description

- Python 3.12.
- FastAPI backend.
- REST API foundation.
- Google OAuth login.
- Google Drive API access.
- Google Drive file reading.
- Document chunking.
- OpenAI embeddings.
- ChromaDB vector store.
- Vector search and semantic search.
- Ask-questions-over-documents endpoint behavior.
- `.env` configuration.
- Docker/Git-ready direction.

## 4. Missing Before Upgrade

- PostgreSQL database schema.
- SQLAlchemy async data layer.
- Alembic migrations.
- Durable conversations and message history.
- Durable agent run traces.
- Workflow agent with multi-step tool execution.
- Tool registry and typed tool contracts.
- Google Sheets API integration.
- Web scraping integration.
- Twilio voice webhooks.
- ElevenLabs text-to-speech.
- Production-grade folder structure.
- Strong README, proposal, and interview collateral.

## 5. Roadmap To 95%+ Match

### Milestone 1: Repository And Proposal Alignment

Files to create:

- `.gitignore`
- `.env.example`
- `pyproject.toml`
- `docs/upwork_alignment.md`

Files to modify:

- `README.md`

Python code:

- Project package metadata and dependency declaration.

FastAPI endpoints:

- Documented target API surface.

Database changes:

- Documented target PostgreSQL schema.

Environment variables:

- Core app, database, OpenAI, Google, Chroma, Twilio, ElevenLabs, scraper.

Commit:

- `docs: align repository with ai platform proposal`

### Milestone 2: PostgreSQL, SQLAlchemy, And Alembic

Files to create:

- `app/core/config.py`
- `app/core/database.py`
- `app/models/*.py`
- `app/repositories/*.py`
- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/202607110001_initial_ai_platform_schema.py`

FastAPI endpoints:

- Database dependency wiring for later routers.

Database changes:

- Create `users`, `documents`, `document_chunks`, `conversations`,
  `messages`, `agent_runs`, `tool_executions`, `sheet_sync_jobs`,
  `scraped_pages`, `voice_sessions`, and `integration_credentials`.

Environment variables:

- `DATABASE_URL`
- `DATABASE_ECHO`

Commit:

- `feat: add async postgres data layer`

### Milestone 3: Google Sheets And Web Scraper

Files to create:

- `app/integrations/google_sheets.py`
- `app/integrations/web_scraper.py`
- `app/services/google_sheets_service.py`
- `app/services/web_scraper_service.py`
- `app/api/v1/endpoints/google_sheets.py`
- `app/api/v1/endpoints/web_scraper.py`

FastAPI endpoints:

- `POST /api/v1/google-sheets/read`
- `POST /api/v1/google-sheets/append`
- `POST /api/v1/scraper/scrape`

Database changes:

- Persist Sheets sync jobs and scraped page records.

Environment variables:

- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `SCRAPER_USER_AGENT`
- `SCRAPER_TIMEOUT_SECONDS`

Commit:

- `feat: add sheets and scraper integrations`

### Milestone 4: Agents, RAG, And Voice

Files to create:

- `app/integrations/openai_client.py`
- `app/integrations/google_drive.py`
- `app/integrations/voice.py`
- `app/rag/*.py`
- `app/agents/*.py`
- `app/services/agent_service.py`
- `app/services/google_drive_service.py`
- `app/services/voice_service.py`
- `app/api/v1/endpoints/agents.py`
- `app/api/v1/endpoints/google_drive.py`
- `app/api/v1/endpoints/voice.py`
- `app/main.py`

FastAPI endpoints:

- `POST /api/v1/google-drive/sync`
- `POST /api/v1/google-drive/search`
- `POST /api/v1/google-drive/ask`
- `POST /api/v1/agents/conversation`
- `POST /api/v1/agents/workflow`
- `POST /api/v1/voice/twilio/inbound`
- `POST /api/v1/voice/synthesize`

Database changes:

- Persist conversations, messages, agent runs, tool executions, documents,
  chunks, and voice sessions.

Environment variables:

- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `CHROMA_PERSIST_DIRECTORY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`

Commit:

- `feat: add agents rag and voice api`

## 6. Architecture Upgrade Strategy

Do not rebuild the Google Drive RAG system. Keep it as the ingestion and
retrieval foundation, then add production layers around it:

- Move Google Drive operations into `app/integrations/google_drive.py`.
- Move chunking, embedding, ChromaDB, and retrieval into `app/rag/`.
- Add PostgreSQL for metadata, conversations, memories, and audit traces.
- Add a `services/` layer for use cases.
- Add `agents/` as orchestration, not as a replacement for the RAG code.
- Add routers under `api/v1/endpoints/`.

## 7. Recommended Folder Structure

```text
app/
  api/v1/endpoints/
  agents/
  core/
  integrations/
  models/
  rag/
  repositories/
  schemas/
  services/
migrations/
docs/
tests/
```

## 8. Recommended PostgreSQL Tables

- `users`: app user and Google account identity.
- `documents`: Google Drive and web document metadata.
- `document_chunks`: chunk text, token count, embedding reference.
- `conversations`: durable chat sessions.
- `messages`: role-based conversation history.
- `agent_runs`: workflow and conversation run records.
- `tool_executions`: individual tool call traces.
- `sheet_sync_jobs`: Google Sheets API activity and row counts.
- `scraped_pages`: fetched page content and status.
- `voice_sessions`: Twilio call and voice transcript state.
- `integration_credentials`: references to securely stored provider credentials.

## 9. Recommended Alembic Migrations

Start with one baseline migration:

- `202607110001_initial_ai_platform_schema.py`

Then split future changes by domain:

- `add_pgvector_embeddings`
- `add_tenant_accounts`
- `add_agent_schedules`
- `add_voice_recordings`
- `add_oauth_token_storage`

## 10. Agent Architecture

Conversation Agent:

- Loads recent message memory from PostgreSQL.
- Retrieves RAG context from document chunks and ChromaDB.
- Calls OpenAI for the final answer.
- Stores user and assistant messages.

Workflow Agent:

- Accepts a goal and optional explicit tool steps.
- Executes tools in order.
- Persists every tool call and result.
- Returns an auditable trace.

Tool Calling:

- Tools are registered in `ToolRegistry`.
- Each tool has a name, description, JSON schema, and async handler.
- Initial tools: `rag.search`, `web.scrape`, `sheets.read`, `sheets.append`.

Memory:

- Conversation history in `messages`.
- Run-level execution memory in `agent_runs`.
- Tool-level trace memory in `tool_executions`.

RAG:

- Google Drive document ingestion.
- Chunking.
- OpenAI embeddings.
- ChromaDB vector lookup.
- PostgreSQL metadata and chunk references.

Google Drive:

- OAuth and Drive API stay as document ingestion capabilities.

Google Sheets:

- Service account or OAuth-backed read/append operations.

Web Scraper:

- Async HTTP fetch.
- HTML title and text extraction.
- Database persistence.

## 11. Upwork Proposal

Hi,

I can help you build this production-ready AI application because my current
backend already covers the most important foundation: FastAPI, REST APIs,
Google Drive ingestion, OpenAI embeddings, ChromaDB vector search, semantic
search, and document Q&A.

I would upgrade it into the exact platform you described by adding PostgreSQL
with SQLAlchemy and Alembic migrations, a durable conversation layer, a
multi-step workflow agent with tool execution, Google Sheets integration, web
scraping, and optional Twilio/ElevenLabs voice support.

My approach is not to rewrite the system. I would preserve the existing Google
Drive RAG foundation, then add a clean production architecture around it:
versioned FastAPI routers, service and repository layers, typed Pydantic
schemas, environment-based configuration, database migrations, auditable agent
run logs, and integration modules for OpenAI, Google Workspace, scraping, and
voice.

Relevant experience I can demonstrate in this repository:

- FastAPI backend architecture.
- OpenAI conversational and embedding workflows.
- RAG over Google Drive documents.
- PostgreSQL schema design and migrations.
- Agent tool-calling workflows.
- Google Sheets automation.
- Web scraping pipelines.
- Twilio and ElevenLabs voice agent design.

I can deliver the project in milestones: first database and migrations, then
Google Sheets and scraper integrations, then conversation/workflow agents, then
voice support, documentation, testing, and deployment readiness.

The result will be a GitHub-ready AI backend that is easy to review, extend,
and deploy.

## 12. Interview Questions And Strong Answers

**Q: How would you avoid rewriting the existing Google Drive RAG system?**

A: I would keep the ingestion, chunking, embedding, and search logic, then move
it behind clean service interfaces. The upgrade adds PostgreSQL metadata,
agent orchestration, and more integrations around the existing RAG foundation.

**Q: How will the workflow agent execute multiple tools safely?**

A: Each tool is registered with a typed schema and async handler. The workflow
agent executes steps sequentially, persists inputs and outputs, and returns an
audit trace. This makes failures debuggable and prevents hidden side effects.

**Q: Why add PostgreSQL if ChromaDB already stores vectors?**

A: ChromaDB is good for vector retrieval, but PostgreSQL is better for durable
business data: users, conversations, documents, sync jobs, tool executions,
voice sessions, and reporting queries.

**Q: How would you integrate Google Sheets?**

A: I would support service-account credentials for backend automation and keep
the integration behind a small service that can read ranges, append rows, and
record sync jobs in PostgreSQL.

**Q: How would you build the voice agent?**

A: Twilio receives calls and speech input, FastAPI handles the webhook,
the Conversation Agent generates the response, and ElevenLabs can synthesize
speech when higher-quality voice output is needed.

**Q: What makes this production-ready?**

A: Versioned APIs, async database sessions, Alembic migrations, typed schemas,
environment configuration, separation of routers/services/repositories, audit
tables for agents, integration boundaries, and documentation.

## 13. Portfolio Screenshots And Demo Videos

Screenshots:

- Swagger UI showing all API groups.
- Alembic migration history.
- PostgreSQL table diagram.
- Agent run trace response with tool executions.
- Google Sheets read/append API response.
- Web scraper response with extracted text.
- RAG answer response with sources.
- Twilio webhook test payload.

Demo videos:

- 2-minute API walkthrough in Swagger.
- Google Drive file ingestion to RAG answer.
- Workflow agent scraping a page and appending a summary to Google Sheets.
- Conversation agent using document memory.
- Twilio voice call triggering the AI agent.
- ElevenLabs text-to-speech response generation.
