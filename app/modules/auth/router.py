from fastapi import APIRouter, Depends, Response, Request, HTTPException 

from sqlalchemy.orm import Session

from authlib.jose.errors import ExpiredTokenError
from authlib.integrations.base_client.errors import OAuthError
from starlette.responses import RedirectResponse


from app.modules.auth import repository
from app.core.database import get_db
from app.modules.auth import service, schemas
from app.modules.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.oauth import oauth

router = APIRouter()

settings = get_settings()

@router.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return service.register_user(db, user)
    
@router.post("/login/")
def login(user: schemas.UserLogin, response: Response, request: Request, db: Session = Depends(get_db)):
    tokens = service.login_user(db, user, request)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=settings.HTTP_ONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_COOKIE_MAX_AGE,
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=settings.HTTP_ONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
        path="/auth"
    )

    return {"message": "Login successful"}

@router.get("/google/login/")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback/", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):

    try:
        token = await oauth.google.authorize_access_token(request)

    except ExpiredTokenError:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?error=time_sync_issue"
        )
        
    except OAuthError as e:
        return RedirectResponse(url=settings.FRONTEND_URL)

    userinfo = token.get("userinfo")
    
    if not userinfo:
        return RedirectResponse(url=settings.FRONTEND_URL)

    email = userinfo["email"]
    username = userinfo["name"]

    user = repository.get_user_by_email(db, email)

    if not user:
        user = repository.create_user(
            db,
            {
                "username": username,
                "email": email,
                "hashed_password": None
            }
        )

    tokens = service.login_user_auth(db, user, request)

    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?login_success=true"
    )

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=settings.HTTP_ONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_COOKIE_MAX_AGE,
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=settings.HTTP_ONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
        path="/auth"
    )

    return response


    
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
    
    tokens = service.refresh_user_token(db, refresh_token, request)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=settings.HTTP_ONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_COOKIE_MAX_AGE,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=settings.HTTP_ONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
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