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


class GoogleDriveClient:
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, *, settings: Settings):
        self.settings = settings

    def _build_service(self) -> Any:
        if service_account is None or build is None:
            raise IntegrationNotConfigured("Google API dependencies are not installed.")
        if not self.settings.google_service_account_file:
            raise IntegrationNotConfigured(
                "GOOGLE_SERVICE_ACCOUNT_FILE is required for Drive sync."
            )

        credentials = service_account.Credentials.from_service_account_file(
            self.settings.google_service_account_file,
            scopes=self.scopes,
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    async def list_files(
        self,
        *,
        folder_id: str | None = None,
        max_files: int = 25,
    ) -> list[dict[str, Any]]:
        def _list() -> list[dict[str, Any]]:
            service = self._build_service()
            query_parts = ["trashed = false"]
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            response = (
                service.files()
                .list(
                    q=" and ".join(query_parts),
                    pageSize=max_files,
                    fields="files(id,name,mimeType,webViewLink,modifiedTime,md5Checksum)",
                )
                .execute()
            )
            return response.get("files", [])

        return await run_in_threadpool(_list)

    async def download_text(self, *, file_id: str, mime_type: str | None = None) -> str:
        def _download() -> str:
            service = self._build_service()
            if mime_type and mime_type.startswith("application/vnd.google-apps"):
                data = service.files().export(fileId=file_id, mimeType="text/plain").execute()
            else:
                data = service.files().get_media(fileId=file_id).execute()
            if isinstance(data, bytes):
                return data.decode("utf-8", errors="ignore")
            return str(data)

        return await run_in_threadpool(_download)
