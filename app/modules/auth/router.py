import structlog

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
from app.core.rate_limiter import limiter

router = APIRouter()

settings = get_settings()

logger = structlog.get_logger()
security_logger = structlog.get_logger("security")

@router.post("/register/", response_model=schemas.UserResponse)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(user: schemas.UserCreate, request:Request, db: Session = Depends(get_db)):
    
    ip = request.client.host

    security_logger.info(
        "register_endpoint_called",
        email=user.email,
        username=user.username,
        ip_address=ip
    )
    
    return service.register_user(db, user)
    
@router.post("/login/")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(user: schemas.UserLogin, response: Response, request: Request, db: Session = Depends(get_db)):
    
    ip = request.client.host

    security_logger.info(
        "login_endpoint_called",
        email=user.email,
        ip_address=ip
    )
    
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
    
    security_logger.info(
        "login_success_cookie_set",
        email=user.email,
        ip_address=ip
    )

    return {"message": "Login successful"}

@router.get("/google/login/")
@limiter.limit("5/minute")
async def google_login(request: Request):
    
    security_logger.info(
        "google_login_redirect",
        ip_address=request.client.host
    )
    
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback/", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    
    ip = request.client.host

    logger.info("google_callback_received", ip_address=ip)

    try:
        token = await oauth.google.authorize_access_token(request)

    except ExpiredTokenError:
        security_logger.warning("google_token_expired", ip_address=ip)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?error=time_sync_issue"
        )
        
    except OAuthError as e:
        security_logger.error("google_oauth_error", ip_address=ip)
        return RedirectResponse(url=settings.FRONTEND_URL)

    userinfo = token.get("userinfo")
    
    if not userinfo:
        security_logger.warning("google_userinfo_missing", ip_address=ip)
        return RedirectResponse(url=settings.FRONTEND_URL)

    email = userinfo["email"]
    username = userinfo["name"]
    
    security_logger.info(
        "google_user_authenticated",
        email=email,
        username=username,
        ip_address=ip
    )

    user = repository.get_user_by_email(db, email)

    if not user:
        logger.info("google_creating_new_user", email=email)
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
    
    security_logger.info(
        "google_login_success",
        email=email,
        ip_address=ip
    )

    return response


    
@router.get("/me/")
def current_user(current_user: schemas.UserResponse = Depends(get_current_user)):
    
    logger.info(
        "current_user_endpoint_called",
        user_id=current_user.id,
        email=current_user.email
    )

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

@router.post("/refresh/")
@limiter.limit(settings.RATE_LIMIT_REFRESH)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    
    ip = request.client.host

    logger.info("refresh_endpoint_called", ip_address=ip)

    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        security_logger.warning("refresh_token_missing", ip_address=ip)
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

    security_logger.info("token_refresh_success", ip_address=ip)
    
    return {"message":"Token refreshed"}

@router.post("/logout/")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
    ):
    
    ip = request.client.host

    security_logger.info("logout_endpoint_called", ip_address=ip)
    
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        security_logger.warning("logout_missing_refresh_token", ip_address=ip)
        raise HTTPException(status_code=401, detail="refrsh token missing")
    
    service.logout(db, refresh_token)
    
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth")

    security_logger.info("logout_success", ip_address=ip)
    
    return {"message":"Logout successfully"}