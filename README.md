# AI Knowledge Platform

An asynchronous FastAPI backend with PostgreSQL persistence, Chroma retrieval,
LangChain model/tool adapters, LlamaIndex ingestion/retrieval, and LangGraph agents.
Existing Google Sheets, scraper, Twilio, and ElevenLabs integrations remain available.

This is an application foundation, **not a complete authorization system**. It does
not provide tenant isolation, exactly-once external writes, automatic reconciliation,
or durable graph resumption. Review the security and failure limitations below
before exposing it publicly.

## Install and run

Use Python 3.12 or newer and PostgreSQL:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
# Set DATABASE_URL and any integration credentials in .env.
alembic upgrade head
uvicorn app.main:app --reload
```

Only run migrations against a database you intend to change. This framework
refactor adds no schema migration. Review any locally generated migrations before
running Alembic; they are not part of this change.

For containers, after configuring the existing Compose environment:

```bash
docker compose up --build -d
```

After changing dependencies, rebuild the image or reinstall the package and restart
Uvicorn. `/health` is a liveness check; it does not verify the database, providers,
or index compatibility. Interactive API documentation: `/docs` and `/redoc`.

The tested framework versions are pinned in `pyproject.toml`:
LangChain core 1.7.0, LangChain OpenAI 1.7.2, LangGraph 1.2.17,
LlamaIndex core 0.14.25, LlamaIndex Chroma 0.6.0, and Chroma 1.5.9.
There was no existing lock file. Package installation still resolves transitive
dependencies; use your deployment's dependency-locking process for reproducible builds.

On the development Mac, Homebrew Python's `pyexpat` linked against an incompatible
system Expat. The verified local workaround was prefixing Python commands with
`DYLD_LIBRARY_PATH=/usr/local/opt/expat/lib`. This is machine-specific, not required
on normal Linux/container installations.

## Actual runtime flow

| Component | Responsibility | Runtime modules |
| --- | --- | --- |
| LangChain | `ChatOpenAI.ainvoke`, conversion of messages, Pydantic-backed `StructuredTool` asynchronous invocation | `app/integrations/openai_client.py`, `app/agents/tool_registry.py`, `app/agents/tools.py` |
| LlamaIndex | Character-counted `TokenTextSplitter`, `TextNode` construction/serialization, Chroma integration and a `BaseRetriever` retaining native distances | `app/rag/chunking.py`, `app/rag/vector_store.py`, `app/rag/service.py` |
| LangGraph | Explicit states, nodes and conditional edges for both agents | `app/agents/conversation_agent.py`, `app/agents/workflow_agent.py` |
| PostgreSQL | Documents, chunks, conversation history, run/tool audit records and integration records | `app/models/`, `app/repositories/` |

Conversation execution:

1. Persist the run and current user message in a short transaction.
2. Load recent history once; the current message is not appended twice.
3. Retrieve only when `use_rag=true`.
4. Generate the answer through LangChain, or use the explicit missing-key fallback.
5. Persist the assistant message and completed run together.

Workflow execution:

1. Use explicit steps, or preserve the original first-URL-to-`web.scrape` inference.
2. Reject requests exceeding the configured step count before calling any tool.
3. Persist tool intent, release the transaction, validate arguments, and execute once.
4. Record the result before proceeding; stop after the first failure.

There are no graph checkpoints, automatic node retries, autonomous model-selected
tools, or cross-request deduplication. A request-local attempted-step guard rejects
re-execution of an already attempted step. Repeating an HTTP request can still
repeat external effects.

The sole tool registry retains `rag.search`, `web.scrape`, `sheets.read`, and
`sheets.append`. Tool schemas derive from Pydantic models instead of a second,
independently maintained JSON-schema registry.

Scraping persists scraped pages as before; it does not automatically ingest every
page into the vector index. Applications ingest through `RagService.index_text`.
No new public ingestion endpoint has been added.

## API compatibility

| Area | Method | Endpoint |
| --- | --- | --- |
| Health | GET | `/health` |
| Google Sheets | POST | `/api/v1/google-sheets/read` |
| Google Sheets | POST | `/api/v1/google-sheets/append` |
| Scraper | POST | `/api/v1/scraper/scrape` |
| Conversation | POST | `/api/v1/agents/conversation` |
| Workflow | POST | `/api/v1/agents/workflow` |
| Twilio | POST | `/api/v1/voice/twilio/inbound` |
| Voice synthesis | POST | `/api/v1/voice/synthesize` |

Success request/response fields remain unchanged, including conversation `sources`
and workflow `results`/`trace`. Agent timeouts return HTTP 504. Index-incompatible
conversation requests return 409. Other uncaught agent errors return a sanitized
502; workflow step failures retain the existing `status="failed"` response shape.
Cancellation is propagated, not converted into a successful response.

## Embeddings, indexes, and score semantics

Defaults are unchanged: `text-embedding-3-small`, Chroma collection
`document_chunks`, and `CHROMA_PERSIST_DIRECTORY=./chroma`. No dimension override is
sent to the embedding provider. Each chunk is embedded once per normal ingestion;
requests are split into batches of up to 128 texts. Neither LlamaIndex nor Chroma
calls an additional embedder: vectors are supplied explicitly, and Chroma's
default embedding function is disabled.

For new records, `LlamaIndex node_id = database chunk_id string = Chroma ID`.
`embedding_id` also records that UUID. Existing legacy records are not rewritten.
Source, title, document/chunk IDs and supplied scalar metadata (including page and
section) travel with the node; complete input metadata stays in PostgreSQL.
The splitter retains character-based size units (1600/200 defaults), but uses
LlamaIndex's boundary handling, so newly ingested chunk boundaries can differ.
Existing chunks are never resplit automatically.

**API `score` means native Chroma distance, lower first.** New Chroma collections
use the existing default squared-L2 metric; a pre-existing collection retains its
metric. The installed stock LlamaIndex Chroma adapter computes `exp(-distance)`.
Our `DistanceRetriever` queries its Chroma client once and retains raw distances;
it never applies an inverse formula. Fixed-vector tests verify distances
`[0, 1, 9]`, ordering, persistence/reopen, and the installed adapter's conversion.
SQL fallback results retain `score=null`.

Vector writes take a process-safe file lock around compatibility validation and
mutation, preventing concurrent application writers from mixing model identities.
Collection metadata is refreshed before validation. External writers that bypass
this application must obey the same compatibility policy.

Collections written by this code store `embedding_model` and
`embedding_dimensions`. A model-name mismatch is incompatible even when dimensions
match. For a nonempty legacy collection without a model marker, every existing
Chroma ID must map to a PostgreSQL chunk recording the configured embedding model.
Unknown IDs, missing evidence, conflicting models, or mismatched dimensions block
unsafe vector operations with `IndexIncompatible`; they do not trigger SQL fallback.
This evidence assumes the recorded model identity is truthful; it cannot detect
manual vector replacement or provider changes behind an unchanged model name.

When OpenAI is unconfigured, ingestion stores SQL chunks without embeddings, and
retrieval uses the existing case-insensitive SQL substring search. When a compatible
vector query returns no hits, the existing SQL fallback also applies. Authentication,
network, and compatibility errors are not treated as missing configuration.

### Existing-index procedure

No automatic index rebuild or data migration is needed when compatibility can be
established. Do not change the model while continuing to use the old collection.
If blocked:

1. Back up PostgreSQL and the Chroma directory while writers are stopped.
2. Check the configured model, collection metadata, and the embedding models of
   the database chunks referenced by existing Chroma IDs.
3. Restore the original model/configuration if the evidence is known. Do not invent
   a model marker merely because dimensions match.
4. If evidence cannot be recovered or a new model is required, plan an explicit,
   separately authorized re-ingestion into a **new empty persistence directory**.
   Re-ingest the original documents using `RagService.index_text`, verify results,
   and only then switch configuration and restart the service. This may incur API
   costs and creates new document/chunk records; this change does not automate it.
5. Retain the old directory for rollback. Never delete it as part of startup.

SQL and Chroma are not one distributed transaction. SQL chunks are committed before
vector persistence; if vector persistence fails, SQL records can remain with
`indexed_at=null`. A cancelled synchronous index operation may finish in its worker.
Inspect both stores before manually retrying; ingestion is not globally idempotent.

## Timeouts, cancellation, retries, and audit records

| Setting | Default | Meaning |
| --- | --- | --- |
| `EXECUTION_TIMEOUT_SECONDS` | 120 | Whole conversation/workflow execution deadline |
| `CALL_TIMEOUT_SECONDS` | 30 | Model, embedding batch, retrieval stage, or tool-call timeout |
| `MAX_TOOL_STEPS` | 20 | Maximum workflow tool calls; validated before dispatch |

The outer deadline bounds all inner awaits, even if a per-call timeout is larger
than the remaining time. Timeout/cancellation audit cleanup has a separate maximum
of 5 seconds, so response teardown can take up to 5 additional seconds. Execution
limits are positive; max tool steps cannot exceed 1000. Graph superstep limits are
also explicit (six for conversation, tool limit plus two for workflow).

Automatic OpenAI SDK, graph-node, Google request, and application retries are
disabled. Answer-generation failures do not rerun retrieval or completed tools.
Sheets uses a four-worker pool and a transport socket timeout; cancelling a queued
request can prevent dispatch, but cancelling a running thread cannot undo a write.
The transport timeout is not a guarantee that a remote service stopped processing.
A discovery-compatible HTTPX transport avoids httplib2's hidden broken-response
replay. Redirects and HTTP error retries are disabled, including token-endpoint
error retries. Chroma and splitting have their own four-worker executor, so
cancelled operations cannot grow the actual number of worker threads unboundedly.

When `sheets.append` times out, is cancelled, or otherwise fails after dispatch
without a confirmed result, its tool record is `uncertain`, with a diagnostic
requiring manual verification. The run is failed or cancelled; no retry occurs.
A synchronous confirmation callback records the provider result before the Sheets
service awaits local database audit. If that audit is interrupted, the confirmed
raw result is retained with `audit_status="not_completed"`.
If a successful provider result was already obtained before audit interruption,
that confirmed result remains completed while the overall run is interrupted.
No code claims that an external effect was rolled back.

Run and tool intent/results use short transactions; no database write transaction
is held across external model/tool calls. Audit cleanup is best effort during
process death, repeated cancellation, or database failure. Inspect leftover
`running`/`uncertain` records manually; there is no reconciliation daemon.

Application logs contain run IDs, failure types, and model timing, without raw
exception text, credentials, complete documents, or tool arguments. Audit tables
still contain application inputs/results as before; protect database access and
retention. Third-party tracing/debug configuration can capture payloads: leave
LangSmith tracing disabled unless separately configured and reviewed.

## Configuration and security limits

See `.env.example` for all variables. `DATABASE_URL` is needed for persisted APIs;
`OPENAI_API_KEY` enables model/embedding calls. Google Sheets, Twilio, and ElevenLabs
credentials remain optional for their respective integrations.

There is no complete request authentication or ownership enforcement in the
existing application. Passing `user_id` or `conversation_id` is not authorization.
Do not expose this backend directly to untrusted users. Add authentication and
ownership checks in a separately scoped change. The scraper also needs deployment-
appropriate SSRF protection, domain restrictions and rate limits; public Twilio
webhooks need request validation. Keep `DEBUG=false` outside local development.
No new framework adapter adds an authorization bypass, and none supplies missing
application-level authorization.

## Isolated tests and checks

The test suite uses fake models/providers, temporary Chroma directories, and unique
schemas in a dedicated disposable PostgreSQL database. It does not consume API
credits, write to Sheets, or touch the application database/index. Start its database:

```bash
docker run --detach --rm --name ai-knowledge-refactor-test \
  -e POSTGRES_PASSWORD=isolated-test-only -e POSTGRES_DB=refactor_test \
  -p 127.0.0.1:55439:5432 postgres:16-alpine
python -m pytest -q
python -m ruff check app tests
python -m mypy app/agents app/rag app/integrations/openai_client.py \
  app/integrations/google_sheets.py app/api/v1/endpoints/agents.py \
  --ignore-missing-imports --follow-imports=silent
python -m pip check
docker stop ai-knowledge-refactor-test
```

Tests deliberately override provider credentials and the database URL. They require
the test database at the listed port; a missing database is a failure, not a skipped
persistence check. The container has no host data volume. The type-check scope above
covers the refactored execution paths, not every legacy integration.

The pre-existing untracked migration
`migrations/versions/147af8e17da7_describe_change.py` has five Ruff findings (import
ordering, unused import, three long lines) and is intentionally not modified.
`ruff check .` therefore reports those findings separately from the changed code.
