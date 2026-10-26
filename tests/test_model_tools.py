import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.agents.tool_registry import RuntimeContext
from app.agents.tools import build_default_tool_registry
from app.core.config import Settings
from app.integrations import openai_client as module
from app.integrations.exceptions import IntegrationNotConfigured


@pytest.fixture(autouse=True)
def block_legacy_provider(monkeypatch):
    monkeypatch.setattr(
        module, "AsyncOpenAI", Mock(side_effect=RuntimeError("legacy provider blocked"))
    )


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


async def test_chat_uses_langchain_messages_and_disables_retries(monkeypatch):
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="answer")))
    factory = Mock(return_value=model)
    monkeypatch.setattr(module, "ChatOpenAI", factory, raising=False)
    client = module.OpenAIClient(settings=settings(openai_api_key="fake"))
    assert await client.chat(messages=[{"role": "user", "content": "hello"}]) == "answer"
    assert factory.call_args.kwargs["max_retries"] == 0
    assert factory.call_args.kwargs["timeout"] == 30
    message = model.ainvoke.call_args.args[0][0]
    assert message.content == "hello"
    assert message.type == "human"


async def test_missing_key_never_constructs_provider(monkeypatch):
    factory = Mock(side_effect=AssertionError("provider constructed"))
    monkeypatch.setattr(module, "ChatOpenAI", factory, raising=False)
    with pytest.raises(IntegrationNotConfigured):
        await module.OpenAIClient(settings=settings()).chat(messages=[])


async def test_provider_failure_is_not_missing_configuration(monkeypatch):
    factory = Mock(
        return_value=SimpleNamespace(ainvoke=AsyncMock(side_effect=RuntimeError("auth")))
    )
    monkeypatch.setattr(module, "ChatOpenAI", factory, raising=False)
    with pytest.raises(RuntimeError, match="auth"):
        await module.OpenAIClient(settings=settings(openai_api_key="fake")).chat(messages=[])


async def test_model_deadline(monkeypatch):
    async def slow(*args):
        await asyncio.sleep(10)

    monkeypatch.setattr(
        module, "ChatOpenAI", Mock(return_value=SimpleNamespace(ainvoke=slow)), raising=False
    )
    with pytest.raises(TimeoutError):
        await module.OpenAIClient(
            settings=settings(openai_api_key="fake", call_timeout_seconds=0.01)
        ).chat(messages=[])


async def test_typed_tools_reject_bad_rag_limit_before_handler():
    rag = SimpleNamespace(search=AsyncMock(return_value=[]))
    registry = build_default_tool_registry()
    context = RuntimeContext(rag_service=rag, web_scraper_service=None, google_sheets_service=None)
    with pytest.raises(ValueError):
        await registry.execute(
            name="rag.search", arguments={"query": "x", "limit": -1}, context=context
        )
    rag.search.assert_not_awaited()


async def test_tools_preserve_names_and_use_async_langchain_adapter():
    registry = build_default_tool_registry()
    assert {t.name for t in registry.list_tools()} == {
        "rag.search",
        "web.scrape",
        "sheets.read",
        "sheets.append",
    }
    rag = SimpleNamespace(search=AsyncMock(return_value=[]))
    context = RuntimeContext(rag_service=rag, web_scraper_service=None, google_sheets_service=None)
    assert await registry.execute(name="rag.search", arguments={"query": "x"}, context=context) == {
        "results": []
    }
    assert registry.list_tools()[0].args_schema is not None
    with pytest.raises(ValueError, match="Unknown tool"):
        await registry.execute(name="missing", arguments={}, context=context)


def test_execution_defaults_and_validation():
    s = settings()
    assert (s.execution_timeout_seconds, s.call_timeout_seconds, s.max_tool_steps) == (120, 30, 20)
    with pytest.raises(ValueError):
        settings(max_tool_steps=0)


async def test_embedding_batches_each_chunk_once_and_orders_response(monkeypatch):
    texts = [str(i) for i in range(260)]
    seen = []

    async def create(**kwargs):
        batch = kwargs["input"]
        seen.extend(batch)
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=i, embedding=[float(text)])
                for i, text in reversed(list(enumerate(batch)))
            ]
        )

    provider = AsyncMock()
    provider.__aenter__.return_value = SimpleNamespace(
        embeddings=SimpleNamespace(create=AsyncMock(side_effect=create))
    )
    factory = Mock(return_value=provider)
    monkeypatch.setattr(module, "AsyncOpenAI", factory)
    vectors = await module.OpenAIClient(settings=settings(openai_api_key="fake")).embed(texts)
    assert seen == texts
    assert vectors == [[float(i)] for i in range(260)]
    assert factory.call_args.kwargs["max_retries"] == 0


async def test_model_cancellation_propagates(monkeypatch):
    model = SimpleNamespace(ainvoke=AsyncMock(side_effect=asyncio.CancelledError()))
    monkeypatch.setattr(module, "ChatOpenAI", Mock(return_value=model))
    with pytest.raises(asyncio.CancelledError):
        await module.OpenAIClient(settings=settings(openai_api_key="fake")).chat(messages=[])


async def test_model_logs_metadata_without_sensitive_payload(monkeypatch, caplog):
    import logging

    model = SimpleNamespace(
        ainvoke=AsyncMock(return_value=SimpleNamespace(content="secret-answer"))
    )
    monkeypatch.setattr(module, "ChatOpenAI", Mock(return_value=model))
    with caplog.at_level(logging.INFO, logger="app.integrations.openai_client"):
        await module.OpenAIClient(settings=settings(openai_api_key="secret-key")).chat(
            messages=[{"role": "user", "content": "secret-document"}]
        )
    assert "duration_ms=" in caplog.text
    assert "gpt-4o-mini" in caplog.text
    assert "secret" not in caplog.text
