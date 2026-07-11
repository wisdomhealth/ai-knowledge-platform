from app.integrations.google_drive import GoogleDriveClient
from app.rag.service import RagService
from app.schemas.agents import RagSourceSchema
from app.schemas.google_drive import (
    DriveSearchRequest,
    DriveSearchResponse,
    DriveSyncRequest,
    DriveSyncResponse,
)


class GoogleDriveService:
    def __init__(self, *, client: GoogleDriveClient, rag_service: RagService):
        self.client = client
        self.rag_service = rag_service

    async def sync(self, payload: DriveSyncRequest) -> DriveSyncResponse:
        files = await self.client.list_files(
            folder_id=payload.folder_id,
            max_files=payload.max_files,
        )
        document_ids = []
        chunks_indexed = 0

        for file in files:
            text = await self.client.download_text(
                file_id=file["id"],
                mime_type=file.get("mimeType"),
            )
            document_id, chunk_count = await self.rag_service.index_text(
                source="google_drive",
                title=file.get("name") or file["id"],
                text=text,
                external_id=file["id"],
                mime_type=file.get("mimeType"),
                url=file.get("webViewLink"),
                checksum=file.get("md5Checksum"),
                metadata={"modified_time": file.get("modifiedTime")},
            )
            document_ids.append(document_id)
            chunks_indexed += chunk_count

        await self.rag_service.session.commit()
        return DriveSyncResponse(
            documents_indexed=len(document_ids),
            chunks_indexed=chunks_indexed,
            document_ids=document_ids,
        )

    async def search(self, payload: DriveSearchRequest) -> DriveSearchResponse:
        results = await self.rag_service.search(query=payload.query, limit=payload.limit)
        return DriveSearchResponse(
            results=[
                RagSourceSchema(
                    document_id=result.document_id,
                    chunk_id=result.chunk_id,
                    title=result.title,
                    content=result.content,
                    score=result.score,
                )
                for result in results
            ]
        )
