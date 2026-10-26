import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.rag.service import RagService
from app.rag.vector_store import ChromaVectorStore


def store_at(path, model="test-model"):
    return ChromaVectorStore(
        settings=Settings(
            _env_file=None,
            chroma_persist_directory=str(path),
            openai_embedding_model=model,
        )
    )


async def test_fixed_vectors_preserve_native_distance_and_order_after_reopen(tmp_path):
    store = store_at(tmp_path)
    ids = [str(uuid.uuid4()) for _ in range(3)]
    await store.add_texts(
        ids=ids,
        texts=["zero", "one", "three"],
        metadatas=[{"chunk_id": i} for i in ids],
        embeddings=[[0.0, 0.0], [1.0, 0.0], [3.0, 0.0]],
    )
    reopened = store_at(tmp_path)
    hits = await reopened.query(query_text="irrelevant", query_embedding=[0.0, 0.0], limit=3)
    assert [hit.id for hit in hits] == ids
    assert [hit.distance for hit in hits] == pytest.approx([0.0, 1.0, 9.0])
    assert [hit.metadata["chunk_id"] for hit in hits] == ids
    # Actual persisted LlamaIndex node serialization, not an unused import.
    collection = reopened._get_collection()
    assert "_node_content" in collection.get(ids=[ids[0]])["metadatas"][0]


async def test_same_dimensions_different_model_is_blocked(tmp_path):
    store = store_at(tmp_path)
    await store.add_texts(
        ids=["one"], texts=["x"], metadatas=[{"chunk_id": "one"}], embeddings=[[1.0, 0.0]]
    )
    other = store_at(tmp_path, model="different-model")
    with pytest.raises(RuntimeError, match="incompatib"):
        await other.query(query_text="x", query_embedding=[1.0, 0.0], limit=1)
    with pytest.raises(RuntimeError, match="incompatib"):
        await other.add_texts(ids=["two"], texts=["y"], metadatas=[{}], embeddings=[[1.0, 0.0]])
    assert store._get_collection().count() == 1


async def test_unmarked_legacy_collection_requires_evidence(tmp_path):
    store = store_at(tmp_path)
    collection = store._get_collection()
    collection.upsert(
        ids=["legacy"],
        documents=["text"],
        metadatas=[{"chunk_id": "legacy"}],
        embeddings=[[1.0, 0.0]],
    )
    with pytest.raises(RuntimeError, match="incompatib"):
        await store.query(query_text="x", query_embedding=[1.0, 0.0], limit=1)
    assert collection.count() == 1


async def test_ingestion_embeds_once_and_preserves_ids_and_metadata(tmp_path, db):
    settings = Settings(_env_file=None, openai_api_key="fake", openai_embedding_model="test-model")

    async def embed(texts):
        assert not db.in_transaction(), "external embedding while database transaction open"
        return [[1.0, 0.0] for _ in texts]

    client = SimpleNamespace(settings=settings, embed=AsyncMock(side_effect=embed))
    store = store_at(tmp_path)
    service = RagService(session=db, openai_client=client, vector_store=store)
    doc_id, count = await service.index_text(
        source="test",
        title="Title",
        text="Some knowledge.",
        metadata={"page": 2, "section": "Intro"},
    )
    assert count == 1
    assert client.embed.await_count == 1
    hits = await service.search(query="knowledge", limit=1)
    assert hits[0].document_id == doc_id
    assert str(hits[0].chunk_id) == store._get_collection().get()["ids"][0]
    assert store._get_collection().get()["metadatas"][0]["page"] == 2
    from sqlalchemy import select

    from app.models.document import DocumentChunk

    chunk = (await db.execute(select(DocumentChunk))).scalar_one()
    assert chunk.embedding_id == str(chunk.id)


async def test_missing_config_uses_database_without_touching_chroma(db):
    from app.integrations.openai_client import OpenAIClient

    client = OpenAIClient(settings=Settings(_env_file=None))
    vector = SimpleNamespace(
        add_texts=AsyncMock(side_effect=AssertionError()),
        query=AsyncMock(side_effect=AssertionError()),
    )
    service = RagService(session=db, openai_client=client, vector_store=vector)
    doc_id, _ = await service.index_text(source="test", title="T", text="offline knowledge")
    hits = await service.search(query="knowledge")
    assert hits[0].document_id == doc_id
    assert hits[0].score is None


async def test_installed_llama_adapter_conversion_matches_native_vectors(tmp_path):
    import math

    from llama_index.core.vector_stores.types import VectorStoreQuery
    from llama_index.vector_stores.chroma import ChromaVectorStore as LlamaStore

    store = store_at(tmp_path)
    await store.add_texts(
        ids=["a", "b", "c"],
        texts=["a", "b", "c"],
        metadatas=[{"chunk_id": x} for x in "abc"],
        embeddings=[[0.0, 0.0], [1.0, 0.0], [3.0, 0.0]],
    )
    stock = LlamaStore(chroma_collection=store._get_collection()).query(
        VectorStoreQuery(query_embedding=[0.0, 0.0], similarity_top_k=3)
    )
    assert stock.similarities == pytest.approx([1.0, math.exp(-1), math.exp(-9)])
    assert [
        hit.distance
        for hit in await store.query(query_text="", query_embedding=[0.0, 0.0], limit=3)
    ] == [0.0, 1.0, 9.0]


async def test_verified_legacy_collection_can_be_read_without_rebuilding(tmp_path, db):
    from app.repositories.document_repository import DocumentRepository

    repo = DocumentRepository(db)
    doc = await repo.create_document(source="legacy", title="Legacy")
    chunk = await repo.add_chunk(
        document_id=doc.id, chunk_index=0, content="legacy text", embedding_model="test-model"
    )
    chunk_id, doc_id = chunk.id, doc.id
    await db.commit()
    store = store_at(tmp_path)
    store._get_collection().upsert(
        ids=[str(chunk_id)],
        documents=["legacy text"],
        metadatas=[{"chunk_id": str(chunk_id), "document_id": str(doc_id), "title": "Legacy"}],
        embeddings=[[1.0, 0.0]],
    )
    client = SimpleNamespace(
        settings=Settings(
            _env_file=None, openai_api_key="fake", openai_embedding_model="test-model"
        ),
        embed=AsyncMock(return_value=[[1.0, 0.0]]),
    )
    hits = await RagService(session=db, openai_client=client, vector_store=store).search(
        query="legacy"
    )
    assert hits[0].chunk_id == chunk_id
    assert hits[0].score == 0
    assert store._get_collection().count() == 1


async def test_incompatibility_does_not_fall_back_to_sql(tmp_path, db):
    store = store_at(tmp_path)
    store._get_collection().upsert(
        ids=[str(uuid.uuid4())], documents=["text"], embeddings=[[1.0, 0.0]]
    )
    client = SimpleNamespace(
        settings=Settings(_env_file=None, openai_api_key="fake"), embed=AsyncMock()
    )
    service = RagService(session=db, openai_client=client, vector_store=store)
    service.documents.search_chunks = AsyncMock(side_effect=AssertionError("unsafe fallback"))
    with pytest.raises(RuntimeError, match="incompatib"):
        await service.search(query="text")
    client.embed.assert_not_awaited()


async def test_upsert_preserves_contract_and_never_uses_default_embedder(tmp_path):
    store = store_at(tmp_path)
    for text in ["old", "new"]:
        await store.add_texts(
            ids=["same"], texts=[text], metadatas=[{"chunk_id": "same"}], embeddings=[[1.0, 0.0]]
        )
    assert store._get_collection().count() == 1
    assert (await store.query(query_text="", query_embedding=[1.0, 0.0], limit=5))[0].text == "new"
    with pytest.raises(ValueError, match="explicit|Explicit"):
        await store.add_texts(ids=["other"], texts=["no embedding"], metadatas=[{}])


def test_chunker_bounds_and_empty_input():
    from app.rag.chunking import chunk_text

    assert chunk_text("   ") == []
    assert all(0 < len(chunk) <= 10 for chunk in chunk_text("a " * 100, max_chars=10, overlap=2))
    with pytest.raises(ValueError):
        chunk_text("x", max_chars=2, overlap=2)


async def test_concurrent_different_models_cannot_mix_vectors(tmp_path):
    import asyncio

    stores = [store_at(tmp_path, model=model) for model in ["model-a", "model-b"]]
    for store in stores:
        store._get_collection()
    outcomes = await asyncio.gather(
        *[
            store.add_texts(
                ids=[str(i)],
                texts=[str(i)],
                metadatas=[{"chunk_id": str(i)}],
                embeddings=[[1.0, 0.0]],
            )
            for i, store in enumerate(stores)
        ],
        return_exceptions=True,
    )
    assert sum(outcome is None for outcome in outcomes) == 1
    assert stores[0]._get_collection().count() == 1


async def test_cancelled_vector_calls_keep_worker_concurrency_bounded(tmp_path, monkeypatch):
    import asyncio
    import threading

    store = store_at(tmp_path)
    release = threading.Event()
    active = 0
    maximum = 0
    lock = threading.Lock()

    def blocked():
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        try:
            release.wait(3)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(store, "_check_compatible", blocked)
    try:
        for _ in range(3):
            tasks = [asyncio.create_task(store.ensure_compatible()) for _ in range(8)]
            await asyncio.sleep(0.05)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        assert maximum <= 4
    finally:
        release.set()
