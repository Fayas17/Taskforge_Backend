from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
# from app.modules.jobs.router import router as jobs_router

from app.core.database import engine, Base, create_schemas

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
# app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_schemas()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@app.get("/")
def health():
    return {"status": "TaskForge running"}