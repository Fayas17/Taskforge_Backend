from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_schemas():
    with engine.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS job"))
        connection.commit()