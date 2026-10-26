import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from filelock import FileLock
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import BaseNode, NodeWithScore, QueryBundle, TextNode
from llama_index.core.vector_stores.utils import metadata_dict_to_node, node_to_metadata_dict
from llama_index.vector_stores.chroma import ChromaVectorStore as LlamaChromaStore

from app.core.config import Settings
from app.integrations.exceptions import IndexIncompatible

_vector_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chroma")


async def run_vector_operation[Result](function: Callable[..., Result], *args: Any) -> Result:
    # Native asyncio cancellation must not release an active-worker capacity token.
    # The executor bounds real worker threads even while cancelled work finishes.
    return await asyncio.wrap_future(_vector_workers.submit(function, *args))


@dataclass(frozen=True)
class VectorHit:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None


class DistanceRetriever(BaseRetriever):
    """LlamaIndex retriever that preserves Chroma's native distances verbatim.

    The stock 0.6.0 adapter transforms distance to exp(-distance). We deliberately
    query its client directly once, avoiding both that lossy conversion and an
    inverse formula. NodeWithScore.score here is distance (lower is better).
    """

    def __init__(self, store: LlamaChromaStore, limit: int):
        super().__init__()
        self.store = store
        self.limit = limit

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        result = self.store.client.query(
            query_embeddings=[query_bundle.embedding],
            n_results=self.limit,
            include=["documents", "metadatas", "distances"],
        )
        nodes = []
        for node_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            metadata = metadata or {}
            if "_node_content" in metadata:
                node = metadata_dict_to_node(metadata, text=text)
            else:
                node = TextNode(id_=node_id, text=text or "", metadata=metadata)
            if node.node_id != node_id:
                raise IndexIncompatible("Index incompatible: node identity mismatch.")
            nodes.append(NodeWithScore(node=node, score=distance))
        return nodes


class ChromaVectorStore:
    collection_name = "document_chunks"

    def __init__(self, *, settings: Settings):
        self.settings = settings
        self._collection: Any | None = None
        self._client: Any | None = None
        self._legacy_evidence: dict[str, str | None] = {}

    def _get_collection(self) -> Any:
        # Called from worker threads in every runtime path, including initialization.
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.settings.chroma_persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        # Refresh metadata: another process may have established the model marker.
        self._collection = self._client.get_or_create_collection(
            self.collection_name,
            embedding_function=None,
        )
        return self._collection

    async def legacy_ids(self) -> list[str]:
        def read() -> list[str]:
            collection = self._get_collection()
            if (collection.metadata or {}).get("embedding_model"):
                return []
            return collection.get(include=[])["ids"]

        return await run_vector_operation(read)

    async def ensure_compatible(self, evidence: dict[str, str | None] | None = None) -> None:
        if evidence is not None:
            self._legacy_evidence = evidence
        await run_vector_operation(self._check_compatible)

    def _check_compatible(self, dimensions: int | None = None) -> None:
        collection = self._get_collection()
        metadata = collection.metadata or {}
        expected = self.settings.openai_embedding_model
        stored_model = metadata.get("embedding_model")
        if stored_model and stored_model != expected:
            raise IndexIncompatible("Index incompatible: embedding model differs.")
        count = collection.count()
        if count and not stored_model:
            ids = collection.get(include=[])["ids"]
            if any(self._legacy_evidence.get(item) != expected for item in ids):
                raise IndexIncompatible(
                    "Index incompatible: legacy embedding identity cannot be established."
                )
        if dimensions is not None and count:
            stored_dimensions = metadata.get("embedding_dimensions")
            if stored_dimensions is None:
                sample = collection.get(limit=1, include=["embeddings"])["embeddings"]
                stored_dimensions = len(sample[0])
            if stored_dimensions != dimensions:
                raise IndexIncompatible("Index incompatible: embedding dimensions differ.")

    async def add_texts(
        self,
        *,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if not texts:
            return
        if embeddings is None or not (len(ids) == len(texts) == len(metadatas) == len(embeddings)):
            raise ValueError("Explicit embeddings and matching input lengths are required.")
        dimensions = len(embeddings[0])
        if not dimensions or any(len(vector) != dimensions for vector in embeddings):
            raise ValueError("Embedding dimensions must be consistent and nonzero.")

        def add() -> None:
            self._get_collection()
            lock_path = Path(self.settings.chroma_persist_directory) / ".embedding-write.lock"
            with FileLock(str(lock_path), timeout=self.settings.call_timeout_seconds):
                self._check_compatible(dimensions)
                collection = self._get_collection()
                # Establish identity before first write; never overwrite a conflicting marker.
                collection.modify(
                    metadata={
                        **(collection.metadata or {}),
                        "embedding_model": self.settings.openai_embedding_model,
                        "embedding_dimensions": dimensions,
                    }
                )
                nodes = [
                    TextNode(id_=item_id, text=text, metadata=metadata, embedding=embedding)
                    for item_id, text, metadata, embedding in zip(
                        ids, texts, metadatas, embeddings, strict=True
                    )
                ]
                adapter = LlamaChromaStore(chroma_collection=collection)
                existing = set(collection.get(ids=ids, include=[])["ids"])
                new_nodes: list[BaseNode] = [node for node in nodes if node.node_id not in existing]
                if new_nodes:
                    adapter.add(new_nodes)
                # Preserve the original upsert contract for caller-supplied existing IDs.
                for node in nodes:
                    if node.node_id in existing:
                        collection.update(
                            ids=[node.node_id],
                            documents=[node.text],
                            embeddings=[node.embedding],
                            metadatas=[
                                node_to_metadata_dict(node, remove_text=True, flat_metadata=True)
                            ],
                        )

        await run_vector_operation(add)

    async def query(
        self,
        *,
        query_text: str,
        query_embedding: list[float] | None,
        limit: int,
    ) -> list[VectorHit]:
        if query_embedding is None:
            raise ValueError("An explicit query embedding is required.")
        if limit < 1:
            raise ValueError("limit must be positive")

        def query() -> list[VectorHit]:
            self._check_compatible(len(query_embedding))
            collection = self._get_collection()
            count = collection.count()
            if not count:
                return []
            retriever = DistanceRetriever(
                LlamaChromaStore(chroma_collection=collection), min(limit, count)
            )
            nodes = retriever.retrieve(QueryBundle(query_str=query_text, embedding=query_embedding))
            return [
                VectorHit(
                    id=node.node.node_id,
                    text=node.node.get_content(),
                    metadata=node.node.metadata,
                    distance=node.score,
                )
                for node in nodes
            ]

        return await run_vector_operation(query)
