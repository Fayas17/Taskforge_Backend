
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from app.core.database import get_db

from app.auth_service import service, schemas
from app.auth_service.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return service.register_user(db, user)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email already registered")
    
@router.post("/login/")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        access_token = service.login_user(db, user)
        return {"access_token": access_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
@router.get("/me/")
def current_user(current_user: schemas.UserResponse = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }