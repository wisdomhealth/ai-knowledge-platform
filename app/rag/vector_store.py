from dataclasses import dataclass
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings

try:
    import chromadb
except ImportError:  # pragma: no cover - dependency is declared for runtime installs
    chromadb = None


@dataclass(frozen=True)
class VectorHit:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None


class ChromaVectorStore:
    collection_name = "document_chunks"

    def __init__(self, *, settings: Settings):
        self.settings = settings
        self._collection: Any | None = None

    def _get_collection(self) -> Any | None:
        if chromadb is None:
            return None
        if self._collection is None:
            client = chromadb.PersistentClient(path=self.settings.chroma_persist_directory)
            self._collection = client.get_or_create_collection(self.collection_name)
        return self._collection

    async def add_texts(
        self,
        *,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        collection = self._get_collection()
        if collection is None or not texts:
            return

        def _add() -> None:
            payload: dict[str, Any] = {
                "ids": ids,
                "documents": texts,
                "metadatas": metadatas,
            }
            if embeddings is not None:
                payload["embeddings"] = embeddings
            collection.upsert(**payload)

        await run_in_threadpool(_add)

    async def query(
        self,
        *,
        query_text: str,
        query_embedding: list[float] | None,
        limit: int,
    ) -> list[VectorHit]:
        collection = self._get_collection()
        if collection is None:
            return []

        def _query() -> list[VectorHit]:
            kwargs: dict[str, Any] = {"n_results": limit}
            if query_embedding:
                kwargs["query_embeddings"] = [query_embedding]
            else:
                kwargs["query_texts"] = [query_text]
            response = collection.query(**kwargs)
            ids = response.get("ids", [[]])[0]
            documents = response.get("documents", [[]])[0]
            metadatas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0] if response.get("distances") else []
            return [
                VectorHit(
                    id=item_id,
                    text=documents[index],
                    metadata=metadatas[index] or {},
                    distance=distances[index] if index < len(distances) else None,
                )
                for index, item_id in enumerate(ids)
            ]

        return await run_in_threadpool(_query)
