
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session
from app.core.database import get_db

from app.auth_service import service, schemas
from app.auth_service.dependencies import get_current_user

security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return service.register_user(db, user)
    
@router.post("/login/")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    access_token = service.login_user(db, user)
    return {"access_token": access_token}

    
@router.get("/me/")
def current_user(current_user: schemas.UserResponse = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

@router.post("/refresh/")
def refresh(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
    refresh_token = credentials.credentials
    return service.refresh_user_token(db, refresh_token)