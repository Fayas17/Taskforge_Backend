import asyncio
import os

import pytest

os.environ["REDIS_URL"] = "memory://"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.rate_limiter import limiter
from app.main import app

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

AsyncTestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Schema + table creation (runs once per test session) ─────────────────────


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create schemas and tables once, drop them after the session."""

    async def _setup():
        async with test_engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS job"))
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    asyncio.get_event_loop().run_until_complete(_setup())
    yield
    asyncio.get_event_loop().run_until_complete(_teardown())


# ── Per-test DB session with automatic rollback ───────────────────────────────


@pytest.fixture()
def db():
    """
    Provides an AsyncSession that wraps every test in a transaction.
    After the test, the transaction is rolled back — no data persists between tests.

    Uses join_transaction_mode="create_savepoint" so that session.commit()
    inside application code creates a SAVEPOINT rather than a real COMMIT,
    allowing the outer rollback to undo everything.
    """

    async def _get_session():
        conn = await test_engine.connect()
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        return conn, session

    async def _close_session(conn, session):
        await session.close()
        await conn.rollback()
        await conn.close()

    conn, session = asyncio.get_event_loop().run_until_complete(_get_session())
    yield session
    asyncio.get_event_loop().run_until_complete(_close_session(conn, session))


# ── TestClient with DB override ───────────────────────────────────────────────


@pytest.fixture()
def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
