"""Start the installed ASGI app with isolated configuration and no providers."""

import os
import socket
import subprocess
import sys
import time

import httpx


def test_isolated_uvicorn_startup(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = {
        **os.environ,
        "OPENAI_API_KEY": "",
        "GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE": "",
        "ELEVENLABS_API_KEY": "",
        "TWILIO_AUTH_TOKEN": "",
        "DEBUG": "false",
        "CHROMA_PERSIST_DIRECTORY": str(tmp_path / "chroma"),
    }
    with (tmp_path / "server.log").open("w+") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=tmp_path,
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 30
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=0.5, trust_env=False
            ) as client:
                while time.monotonic() < deadline:
                    try:
                        response = client.get("/health")
                        break
                    except httpx.TransportError:
                        if process.poll() is not None:
                            log.seek(0)
                            raise AssertionError(log.read()) from None
                        time.sleep(0.05)
                else:
                    raise AssertionError("isolated server did not become ready")
                assert response.status_code == 200
                assert response.json() == {"status": "ok"}
                assert "/api/v1/agents/workflow" in client.get("/openapi.json").json()["paths"]
                assert not (tmp_path / "chroma").exists(), "startup must not open/create an index"
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
