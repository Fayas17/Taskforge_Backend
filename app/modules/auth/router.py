from fastapi import APIRouter, Depends, Response, Request, HTTPException

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth import service, schemas
from app.modules.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return service.register_user(db, user)
    
@router.post("/login/")
def login(user: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    tokens = service.login_user(db, user)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        path="/auth"
    )

    return {"message": "Login successful"}


    
@router.get("/me/")
def current_user(current_user: schemas.UserResponse = Depends(get_current_user)):

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

@router.post("/refresh/")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token is missing")
    
    tokens = service.refresh_user_token(db, refresh_token)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"] ,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        path="/auth"
    )

    return {"message":"Token refreshed"}

@router.post("/logout/")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
    ):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="refrsh token missing")
    
    service.logout(db, refresh_token)
    
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth")

    return {"message":"Logout successfully"}