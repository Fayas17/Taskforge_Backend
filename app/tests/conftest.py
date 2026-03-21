import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
import pytest_asyncio

os.environ["REDIS_URL"] = "memory://"

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import Base, get_db
from app.core.rate_limiter import limiter
from app.main import app


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Skip the real lifespan so the app's engine never touches test loops."""
    yield


# Disable rate limiting during tests
limiter.enabled = False

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('TEST_POSTGRES_USER')}:"
    f"{os.getenv('TEST_POSTGRES_PASSWORD')}@"
    f"{os.getenv('TEST_POSTGRES_HOST')}:"
    f"{os.getenv('TEST_POSTGRES_PORT')}/"
    f"{os.getenv('TEST_POSTGRES_DB')}"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


# ── Schema + table creation (runs once per test session) ─────────────────────


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create schemas and tables once, drop them after the session."""

    async def _setup() -> None:
        async with test_engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS job"))
            await conn.run_sync(Base.metadata.create_all)
        # Release pool connections: asyncio.run() uses a temporary loop that
        # closes after this call, so we must not leave connections in the pool.
        await test_engine.dispose()

    async def _teardown() -> None:
        # Use a fresh engine — test_engine's pool may hold connections from
        # closed test loops; a new engine always starts clean.
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


# ── Per-test DB session with automatic rollback ───────────────────────────────


@pytest_asyncio.fixture()
async def db() -> AsyncSession:  # type: ignore[override]
    """
    Wraps every test in a transaction that is rolled back after the test.
    Uses join_transaction_mode="create_savepoint" so that session.commit()
    inside application code creates a SAVEPOINT rather than a real COMMIT,
    allowing the outer rollback to undo everything.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()
    # Dispose after each test so the pool doesn't carry connections across
    # event loops (each test runs in its own loop with asyncio_mode=auto).
    await test_engine.dispose()


# ── Async HTTP client with DB override ───────────────────────────────────────


@pytest_asyncio.fixture()
async def client(db: AsyncSession) -> httpx.AsyncClient:  # type: ignore[override]
    """AsyncClient that talks to the app in-process via ASGITransport."""

    async def override_get_db():  # type: ignore[return]
        yield db

    app.dependency_overrides[get_db] = override_get_db
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.router.lifespan_context = original_lifespan
    app.dependency_overrides.clear()
