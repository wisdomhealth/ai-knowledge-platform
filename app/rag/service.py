import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.exceptions import IntegrationNotConfigured
from app.integrations.openai_client import OpenAIClient
from app.rag.chunking import chunk_text
from app.rag.vector_store import ChromaVectorStore
from app.repositories.document_repository import DocumentRepository


@dataclass(frozen=True)
class RagSource:
    document_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    title: str | None
    content: str
    score: float | None = None


class RagService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        openai_client: OpenAIClient,
        vector_store: ChromaVectorStore,
    ):
        self.session = session
        self.openai_client = openai_client
        self.vector_store = vector_store
        self.documents = DocumentRepository(session)

    async def index_text(
        self,
        *,
        source: str,
        title: str,
        text: str,
        owner_id: uuid.UUID | None = None,
        external_id: str | None = None,
        mime_type: str | None = None,
        url: str | None = None,
        checksum: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[uuid.UUID, int]:
        document = await self.documents.create_document(
            source=source,
            title=title,
            owner_id=owner_id,
            external_id=external_id,
            mime_type=mime_type,
            url=url,
            checksum=checksum,
            metadata=metadata,
        )
        chunks = chunk_text(text)
        embeddings: list[list[float]] | None = None
        try:
            embeddings = await self.openai_client.embed(chunks) if chunks else None
        except IntegrationNotConfigured:
            embeddings = None

        vector_ids: list[str] = []
        vector_texts: list[str] = []
        vector_metadatas: list[dict] = []
        for index, chunk in enumerate(chunks):
            chunk_model = await self.documents.add_chunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                token_count=None,
                embedding_id=f"{document.id}:{index}",
                embedding_model=self.openai_client.settings.openai_embedding_model,
                metadata={"source": source, "title": title},
            )
            vector_ids.append(str(chunk_model.id))
            vector_texts.append(chunk)
            vector_metadatas.append(
                {
                    "document_id": str(document.id),
                    "chunk_id": str(chunk_model.id),
                    "title": title,
                    "source": source,
                }
            )

        if embeddings:
            await self.vector_store.add_texts(
                ids=vector_ids,
                texts=vector_texts,
                metadatas=vector_metadatas,
                embeddings=embeddings,
            )
        return document.id, len(chunks)

    async def search(self, *, query: str, limit: int = 5) -> list[RagSource]:
        query_embedding: list[float] | None = None
        try:
            embeddings = await self.openai_client.embed([query])
            query_embedding = embeddings[0] if embeddings else None
        except IntegrationNotConfigured:
            query_embedding = None

        vector_hits = []
        if query_embedding:
            vector_hits = await self.vector_store.query(
                query_text=query,
                query_embedding=query_embedding,
                limit=limit,
            )
        if vector_hits:
            return [
                RagSource(
                    document_id=uuid.UUID(hit.metadata["document_id"])
                    if hit.metadata.get("document_id")
                    else None,
                    chunk_id=uuid.UUID(hit.metadata["chunk_id"])
                    if hit.metadata.get("chunk_id")
                    else None,
                    title=hit.metadata.get("title"),
                    content=hit.text,
                    score=hit.distance,
                )
                for hit in vector_hits
            ]

        chunks = await self.documents.search_chunks(query, limit=limit)
        return [
            RagSource(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                title=None,
                content=chunk.content,
                score=None,
            )
            for chunk in chunks
        ]
