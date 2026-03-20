from fastapi import FastAPI
from app.core.database import Base, engine, create_schemas
import app.auth_service.models
import app.job_service.models

app = FastAPI(title="TaskForge")


@app.on_event("startup")
def startup():
    create_schemas()
    Base.metadata.create_all(bind=engine)


@app.get("/")
def health():
    return {"status": "TaskForge running"}
