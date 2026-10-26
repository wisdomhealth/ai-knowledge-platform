import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.integrations.google_sheets import GoogleSheetsClient


async def test_sheets_thread_wait_can_be_cancelled_without_retry(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    calls = []

    def execute(**kwargs):
        calls.append(kwargs)
        started.set()
        release.wait(2)
        return {"updates": {"updatedRows": 1}}

    request = SimpleNamespace(execute=execute)
    values = SimpleNamespace(append=Mock(return_value=request))
    service = SimpleNamespace(spreadsheets=lambda: SimpleNamespace(values=lambda: values))
    client = GoogleSheetsClient(settings=Settings(_env_file=None))
    monkeypatch.setattr(client, "_build_service", lambda: service)
    task = asyncio.create_task(
        client.append_rows(spreadsheet_id="fake", range_name="Sheet1", values=[[1]])
    )
    try:
        async with asyncio.timeout(1):
            while not started.is_set():
                await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=0.2)
        assert calls == [{"num_retries": 0}]
    finally:
        release.set()


def test_transport_timeout_and_no_discovery_cache(monkeypatch):
    from app.integrations import google_sheets as module

    factory = Mock()
    monkeypatch.setattr(module, "build", factory)
    monkeypatch.setattr(
        module.service_account.Credentials, "from_service_account_file", Mock(return_value=Mock())
    )
    client = GoogleSheetsClient(
        settings=Settings(
            _env_file=None, google_sheets_service_account_file="fake", call_timeout_seconds=7
        )
    )
    client._build_service()
    assert factory.call_args.kwargs["http"].http.timeout == 7
    assert factory.call_args.kwargs["cache_discovery"] is False


def test_single_attempt_transport_does_not_replay_lost_response(monkeypatch):
    import httpx

    from app.integrations import google_sheets as module

    transport_cls = getattr(module, "SingleAttemptHttp", None)
    assert transport_cls is not None, "Sheets must use a transport without httplib2 replay"
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.RemoteProtocolError("response lost after write")

    client_cls = httpx.Client
    monkeypatch.setattr(
        module.httpx, "Client", lambda **kwargs: client_cls(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(httpx.RemoteProtocolError):
        transport_cls(timeout=1).request("https://example.test/append", method="POST", body=b"data")
    assert len(calls) == 1


def test_token_error_is_not_retried_by_google_auth(monkeypatch):
    import httpx
    from google.oauth2 import _client
    from google_auth_httplib2 import Request

    from app.integrations import google_sheets as module

    transport_cls = getattr(module, "SingleAttemptHttp", None)
    assert transport_cls is not None
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={"error": "server_error"})

    client_cls = httpx.Client
    monkeypatch.setattr(
        module.httpx, "Client", lambda **kwargs: client_cls(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(httpx.HTTPStatusError):
        _client.jwt_grant(Request(transport_cls(timeout=1)), "https://example.test/token", b"fake")
    assert len(calls) == 1
