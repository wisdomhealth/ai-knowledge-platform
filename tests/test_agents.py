import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from sqlalchemy import select

from app.agents.conversation_agent import ConversationAgent
from app.agents.memory import ConversationMemory
from app.agents.tool_registry import RuntimeContext, ToolDefinition, ToolRegistry
from app.agents.workflow_agent import WorkflowAgent
from app.core.config import Settings
from app.models import AgentRun, Message, ToolExecution
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agents import ConversationRequest, WorkflowRequest, WorkflowStep


class EmptyArgs(BaseModel):
    pass


def build_workflow(db, handler, name="sheets.append", **limits):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name=name, description="test tool", args_schema=EmptyArgs, handler=handler)
    )
    return WorkflowAgent(
        repository=ConversationRepository(db),
        registry=registry,
        runtime_context=RuntimeContext(None, None, None),
        settings=Settings(_env_file=None, **limits),
    )


async def test_workflow_runs_graph_in_order_and_commits_before_external_calls(db):
    calls = []

    async def handler(args, context):
        assert not db.in_transaction()
        calls.append(len(calls))
        return {"position": calls[-1]}

    agent = build_workflow(db, handler)
    response = await agent.run(
        WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="sheets.append")] * 2)
    )
    assert response.status == "completed"
    assert calls == [0, 1]
    assert len(response.trace) == 2
    assert agent.graph is not None
    records = (await db.execute(select(ToolExecution))).scalars().all()
    assert len(records) == 2
    assert all(record.status == "completed" for record in records)


async def test_workflow_failure_stops_and_sanitizes_errors(db):
    calls = []

    async def handler(args, context):
        calls.append(1)
        raise RuntimeError("SECRET-token")

    response = await build_workflow(db, handler, name="rag.search").run(
        WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="rag.search")] * 2)
    )
    assert response.status == "failed"
    assert len(calls) == 1
    assert "SECRET" not in response.model_dump_json()
    run = await db.get(AgentRun, response.run_id)
    assert run.status == "failed"
    execution = (await db.execute(select(ToolExecution))).scalar_one()
    assert execution.status == "failed"
    assert "SECRET" not in execution.error


@pytest.mark.parametrize("cancel", [False, True])
async def test_append_timeout_or_cancellation_is_uncertain_and_never_repeated(db, cancel):
    started = asyncio.Event()
    calls = []

    async def handler(args, context):
        calls.append(1)
        started.set()
        await asyncio.sleep(10)

    agent = build_workflow(db, handler, call_timeout_seconds=0.05)
    task = asyncio.create_task(
        agent.run(WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="sheets.append")] * 2))
    )
    await started.wait()
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
        await task
    assert len(calls) == 1
    execution = (await db.execute(select(ToolExecution))).scalar_one()
    assert execution.status == "uncertain"
    assert "uncertain" in execution.error.lower()
    run = (await db.execute(select(AgentRun))).scalar_one()
    assert run.status == ("cancelled" if cancel else "failed")


async def test_overall_deadline_bounds_tool_timeout(db):
    async def handler(args, context):
        await asyncio.sleep(10)

    agent = build_workflow(db, handler, execution_timeout_seconds=1, call_timeout_seconds=30)
    with pytest.raises(TimeoutError):
        await agent.run(
            WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="sheets.append")])
        )
    execution = (await db.execute(select(ToolExecution))).scalar_one()
    assert execution.status == "uncertain"
    run = (await db.execute(select(AgentRun))).scalar_one()
    assert run.status == "failed"


async def test_step_limit_prevents_any_tool_calls(db):
    handler = AsyncMock()
    agent = build_workflow(db, handler, max_tool_steps=1)
    response = await agent.run(
        WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="sheets.append")] * 2)
    )
    assert response.status == "failed"
    handler.assert_not_awaited()


async def test_unknown_tool_and_empty_steps(db):
    agent = build_workflow(db, AsyncMock())
    empty = await agent.run(WorkflowRequest(goal="nothing to infer"))
    assert empty.trace == [{"event": "no_steps", "reason": "No explicit or inferred tool steps."}]
    missing = await agent.run(
        WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="missing")])
    )
    assert missing.status == "failed"
    assert "Unknown tool" in missing.results[0]["error"]


async def test_conversation_history_once_and_skip_rag(db):
    repository = ConversationRepository(db)
    conversation = await repository.create_conversation(title="test")
    await repository.add_message(conversation_id=conversation.id, role="user", content="previous")
    await db.commit()

    async def chat(**kwargs):
        assert not db.in_transaction()
        assert [m["content"] for m in kwargs["messages"]].count("current") == 1
        assert any(m["content"] == "previous" for m in kwargs["messages"])
        return "answer"

    client = SimpleNamespace(settings=Settings(_env_file=None), chat=AsyncMock(side_effect=chat))
    rag = SimpleNamespace(search=AsyncMock(side_effect=AssertionError("unexpected retrieval")))
    agent = ConversationAgent(
        repository=repository,
        memory=ConversationMemory(repository=repository),
        openai_client=client,
        rag_service=rag,
    )
    response = await agent.respond(
        ConversationRequest(message="current", conversation_id=conversation.id, use_rag=False)
    )
    assert response.answer == "answer"
    assert response.sources == []
    assert agent.graph is not None
    assert (await db.get(AgentRun, response.run_id)).status == "completed"
    assert len((await db.execute(select(Message))).scalars().all()) == 3


@pytest.mark.parametrize(
    "failure", [RuntimeError("secret-key"), TimeoutError(), asyncio.CancelledError()]
)
async def test_conversation_failures_persist_without_success(db, failure):
    repository = ConversationRepository(db)
    client = SimpleNamespace(settings=Settings(_env_file=None), chat=AsyncMock(side_effect=failure))
    agent = ConversationAgent(
        repository=repository,
        memory=ConversationMemory(repository=repository),
        openai_client=client,
        rag_service=SimpleNamespace(search=AsyncMock(return_value=[])),
    )
    with pytest.raises(type(failure)):
        await agent.respond(ConversationRequest(message="test"))
    run = (await db.execute(select(AgentRun))).scalar_one()
    assert run.status == ("cancelled" if isinstance(failure, asyncio.CancelledError) else "failed")
    assert "secret" not in str(run.output_json)
    assert len((await db.execute(select(Message))).scalars().all()) == 1


async def test_confirmed_write_stays_completed_if_audit_is_interrupted(db, monkeypatch):
    handler = AsyncMock(return_value={"updated_rows": 1})
    agent = build_workflow(db, handler)
    original = agent.repository.finish_tool_execution
    interrupted = False

    async def finish(*args, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise asyncio.CancelledError()
        await original(*args, **kwargs)

    monkeypatch.setattr(agent.repository, "finish_tool_execution", finish)
    with pytest.raises(asyncio.CancelledError):
        await agent.run(
            WorkflowRequest(goal="test", steps=[WorkflowStep(tool_name="sheets.append")])
        )
    handler.assert_awaited_once()
    execution = (await db.execute(select(ToolExecution))).scalar_one()
    assert execution.status == "completed"
    assert execution.result == {"updated_rows": 1}
    assert (await db.execute(select(AgentRun))).scalar_one().status == "cancelled"


async def test_invalid_tool_arguments_are_audited_without_dispatch(db):
    from app.agents.tools import build_default_tool_registry

    rag = SimpleNamespace(search=AsyncMock())
    agent = WorkflowAgent(
        repository=ConversationRepository(db),
        registry=build_default_tool_registry(),
        runtime_context=RuntimeContext(rag, None, None),
    )
    response = await agent.run(
        WorkflowRequest(
            goal="invalid",
            steps=[WorkflowStep(tool_name="rag.search", arguments={"query": "x", "limit": -1})],
        )
    )
    assert response.status == "failed"
    rag.search.assert_not_awaited()
    assert (await db.execute(select(ToolExecution))).scalar_one().status == "failed"


async def test_missing_model_configuration_keeps_explicit_conversation_fallback(db):
    import uuid

    from app.integrations.openai_client import OpenAIClient
    from app.rag.service import RagSource

    repository = ConversationRepository(db)
    source = RagSource(uuid.uuid4(), uuid.uuid4(), "Title", "context", 1.0)
    agent = ConversationAgent(
        repository=repository,
        memory=ConversationMemory(repository=repository),
        openai_client=OpenAIClient(settings=Settings(_env_file=None)),
        rag_service=SimpleNamespace(search=AsyncMock(return_value=[source])),
    )
    response = await agent.respond(ConversationRequest(message="test"))
    assert response.answer.startswith(
        "OpenAI is not configured, but I found relevant indexed context:"
    )
    assert response.sources[0].chunk_id == source.chunk_id
    assert response.sources[0].score == 1.0


async def test_url_inference_is_preserved(db):
    import uuid

    from app.agents.tools import build_default_tool_registry

    scraper = SimpleNamespace(
        scrape=AsyncMock(
            return_value=SimpleNamespace(model_dump=lambda **kw: {"page_id": str(uuid.uuid4())})
        )
    )
    agent = WorkflowAgent(
        repository=ConversationRepository(db),
        registry=build_default_tool_registry(),
        runtime_context=RuntimeContext(None, scraper, None),
    )
    response = await agent.run(WorkflowRequest(goal="Read https://example.test/page"))
    assert response.status == "completed"
    scraper.scrape.assert_awaited_once()
    assert str(scraper.scrape.call_args.args[0].url) == "https://example.test/page"


@pytest.mark.parametrize(
    "failure", [asyncio.CancelledError(), TimeoutError(), RuntimeError("audit")]
)
async def test_real_sheets_service_confirmation_survives_audit_failure(db, monkeypatch, failure):
    from app.agents.tools import build_default_tool_registry
    from app.services.google_sheets_service import GoogleSheetsService

    client = SimpleNamespace(append_rows=AsyncMock(return_value={"updates": {"updatedRows": 1}}))
    sheets = GoogleSheetsService(session=db, client=client)
    monkeypatch.setattr(sheets.documents, "record_sheet_job", AsyncMock(side_effect=failure))
    agent = WorkflowAgent(
        repository=ConversationRepository(db),
        registry=build_default_tool_registry(),
        runtime_context=RuntimeContext(None, None, sheets),
    )
    request = WorkflowRequest(
        goal="append",
        steps=[
            WorkflowStep(
                tool_name="sheets.append",
                arguments={"spreadsheet_id": "fake", "range_name": "Sheet1", "values": [[1]]},
            )
        ],
    )
    if isinstance(failure, (asyncio.CancelledError, TimeoutError)):
        with pytest.raises(type(failure)):
            await agent.run(request)
    else:
        assert (await agent.run(request)).status == "failed"
    client.append_rows.assert_awaited_once()
    execution = (await db.execute(select(ToolExecution))).scalar_one()
    assert execution.status == "completed"
    assert execution.result["raw_result"]["updates"]["updatedRows"] == 1
