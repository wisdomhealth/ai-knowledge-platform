"""Never inherit business credentials or persistence settings in tests."""

import os

os.environ.update(
    DATABASE_URL="postgresql+asyncpg://postgres:isolated-test-only@127.0.0.1:55439/refactor_test",
    OPENAI_API_KEY="",
    GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE="",
    CHROMA_PERSIST_DIRECTORY="/tmp/unused-ai-knowledge-test-chroma",
    LANGSMITH_TRACING="false",
    ANONYMIZED_TELEMETRY="False",
)

import uuid

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base


@pytest_asyncio.fixture
async def db():
    # Unique schema in the dedicated disposable database; no DROP against public.
    engine = create_async_engine(os.environ["DATABASE_URL"])
    schema = "test_" + uuid.uuid4().hex
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(text(f'SET search_path TO "{schema}"'))
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
    engine = create_async_engine(
        os.environ["DATABASE_URL"], connect_args={"server_settings": {"search_path": schema}}
    )
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()
    cleanup = create_async_engine(os.environ["DATABASE_URL"])
    async with cleanup.begin() as connection:
        await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await cleanup.dispose()
