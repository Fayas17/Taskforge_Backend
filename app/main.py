from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.logging import setup_logging

setup_logging()

from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from fastapi.responses import JSONResponse

from app.middleware.request_logger import RequestLoggingMiddleware

from app.core.config import get_settings
from app.core.rate_limiter import limiter
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

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"}
    )

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
# app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])

app.add_middleware(RequestLoggingMiddleware)

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