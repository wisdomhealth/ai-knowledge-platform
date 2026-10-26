from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_agent_service
from app.integrations.exceptions import IndexIncompatible
from app.main import create_app


@pytest.mark.parametrize(
    "error,code",
    [
        (RuntimeError("secret-value"), 502),
        (TimeoutError(), 504),
        (IndexIncompatible("secret-value"), 409),
    ],
)
def test_agent_errors_are_explicit_and_sanitized(error, code):
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: SimpleNamespace(
        conversation=AsyncMock(side_effect=error)
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/agents/conversation", json={"message": "test"})
    assert response.status_code == code
    assert "secret-value" not in response.text
    assert "detail" in response.json()


def test_existing_routes_and_response_fields():
    schema = create_app().openapi()
    assert {
        "/health",
        "/api/v1/agents/conversation",
        "/api/v1/agents/workflow",
        "/api/v1/google-sheets/read",
        "/api/v1/google-sheets/append",
        "/api/v1/scraper/scrape",
        "/api/v1/voice/twilio/inbound",
        "/api/v1/voice/synthesize",
    } <= set(schema["paths"])
    models = schema["components"]["schemas"]
    assert set(models["ConversationResponse"]["properties"]) == {
        "conversation_id",
        "run_id",
        "user_message_id",
        "assistant_message_id",
        "answer",
        "sources",
    }
    assert set(models["WorkflowResponse"]["properties"]) == {"run_id", "status", "results", "trace"}
