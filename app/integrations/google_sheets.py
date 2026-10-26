import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httplib2
import httpx
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build

from app.core.config import Settings
from app.integrations.exceptions import IntegrationNotConfigured

_sheets_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sheets")


class SingleAttemptHttp(httplib2.Http):
    """Discovery-compatible HTTP interface with no hidden connection replay.

    httplib2 retries some broken responses even with RETRIES=1. Use HTTPX's
    single-attempt transport instead. Non-2xx responses raise immediately so
    google-auth's token-refresh backoff cannot silently issue another request.
    """

    def request(self, uri, method="GET", body=None, headers=None, **kwargs):
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=False,
            transport=httpx.HTTPTransport(retries=0),
        ) as client:
            response = client.request(method, uri, content=body, headers=headers)
            response.raise_for_status()
            return httplib2.Response(
                {**dict(response.headers), "status": str(response.status_code)}
            ), response.content


class GoogleSheetsClient:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self, *, settings: Settings):
        self.settings = settings

    def _build_service(self) -> Any:
        if not self.settings.google_sheets_service_account_file:
            raise IntegrationNotConfigured(
                "GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE is required for Sheets."
            )

        credentials = service_account.Credentials.from_service_account_file(
            self.settings.google_sheets_service_account_file,
            scopes=self.scopes,
        )
        http = AuthorizedHttp(
            credentials,
            http=SingleAttemptHttp(timeout=self.settings.call_timeout_seconds),
            max_refresh_attempts=0,
        )
        return build("sheets", "v4", http=http, cache_discovery=False, num_retries=0)

    async def read_range(self, *, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        def _read() -> list[list[Any]]:
            service = self._build_service()
            response = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute(num_retries=0)
            )
            return response.get("values", [])

        async with asyncio.timeout(self.settings.call_timeout_seconds):
            return await asyncio.wrap_future(_sheets_workers.submit(_read))

    async def append_rows(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
    ) -> dict[str, Any]:
        def _append() -> dict[str, Any]:
            service = self._build_service()
            return (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": values},
                )
                .execute(num_retries=0)
            )

        # Cancelling this await cannot undo an already dispatched remote write.
        # The workflow records uncertainty; this worker never retries the append.
        async with asyncio.timeout(self.settings.call_timeout_seconds):
            return await asyncio.wrap_future(_sheets_workers.submit(_append))
