
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from app.core.database import get_db

from app.auth_service import service, schemas

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return service.register_user(db, user)
    except HTTPException as e:
        raise e
    
@router.post("/login/")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        access_token = service.login_user(db, user)
        return {"access_token": access_token}
    except HTTPException as e:
        raise e