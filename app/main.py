from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.modules.auth.router import router as auth_router
# from app.modules.jobs.router import router as jobs_router
from app.core.database import engine, Base, create_schemas



@asynccontextmanager
async def lifespan(app: FastAPI):
    create_schemas()
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

settings = get_settings()

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
# app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])


origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def health():
    return {"status": "TaskForge running"}