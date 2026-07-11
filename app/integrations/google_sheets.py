from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.integrations.exceptions import IntegrationNotConfigured

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - dependency is declared for runtime installs
    service_account = None
    build = None


class GoogleSheetsClient:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self, *, settings: Settings):
        self.settings = settings

    def _build_service(self) -> Any:
        if service_account is None or build is None:
            raise IntegrationNotConfigured("Google API dependencies are not installed.")
        if not self.settings.google_service_account_file:
            raise IntegrationNotConfigured("GOOGLE_SERVICE_ACCOUNT_FILE is required for Sheets.")

        credentials = service_account.Credentials.from_service_account_file(
            self.settings.google_service_account_file,
            scopes=self.scopes,
        )
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    async def read_range(self, *, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        def _read() -> list[list[Any]]:
            service = self._build_service()
            response = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            return response.get("values", [])

        return await run_in_threadpool(_read)

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
                .execute()
            )

        return await run_in_threadpool(_append)
