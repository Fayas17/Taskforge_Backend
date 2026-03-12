import os
import pytest

# MNC Best Practice: Isolate tests from production infrastructure
# Set this BEFORE any app imports so the rate limiter picks it up immediately.
os.environ["REDIS_URL"] = "memory://"

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.rate_limiter import limiter

# Disable rate limiting for testing by default
limiter.enabled = False


TEST_DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('TEST_POSTGRES_USER')}:"
    f"{os.getenv('TEST_POSTGRES_PASSWORD')}@"
    f"{os.getenv('TEST_POSTGRES_HOST')}:"
    f"{os.getenv('TEST_POSTGRES_PORT')}/"
    f"{os.getenv('TEST_POSTGRES_DB')}"
)

engine = create_engine(
    TEST_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    with engine.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS job"))
        connection.commit()

    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    connection = engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c