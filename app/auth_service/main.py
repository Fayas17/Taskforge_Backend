from fastapi import FastAPI
from app.core.database import engine, Base, create_schemas

from app.auth_service import router
import app.auth_service.models

app = FastAPI()



app.include_router(router.router)


@app.on_event("startup")
def on_startup():
    create_schemas()
    Base.metadata.create_all(bind=engine)

@app.get("/")
def health():
    return {"status": "Auth service running"}