import structlog

from fastapi import HTTPException

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from jose import jwt, JWTError

from datetime import datetime, timedelta

from app.core.config import get_settings
from app.modules.auth import repository
from app.modules.auth.utils import hash_password, verify_password, hash_jti, create_access_token, create_refresh_token

settings = get_settings()

logger = structlog.get_logger()
security_logger = structlog.get_logger("security")

def register_user(db: Session, user_input):
    
    security_logger.info(
        "register_attempt",
        username=user_input.username,
        email=user_input.email
    )
    
    existing_user = repository.get_user_by_username(db, user_input.username)
    
    if existing_user:
        security_logger.warning(
            "register_failed_username_taken",
            username=user_input.username
        )
        raise HTTPException(status_code=400, detail="Username already taken")
    
    existing_user = repository.get_user_by_email(db, user_input.email)
    
    if existing_user:
        security_logger.warning(
            "register_failed_email_taken",
            username=user_input.username
        )
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user_input.password) < 8:
        security_logger.warning(
            "register_failed_password_policy",
            email=user_input.email
        )
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    user_data = {
        "username": user_input.username,
        "email": user_input.email,
        "hashed_password": hash_password(user_input.password),
    }

    try:
        return repository.create_user(db, user_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already registered")

def login_user(db: Session, user_input, request):
    
    email = user_input.email

    security_logger.info(
        "login_attempt",
        email=email
    )
    
    user = repository.get_user_by_email(db, user_input.email)
    
    if not user:
        security_logger.warning(
            "login_failed_user_not_found",
            email=email
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(user_input.password, user.hashed_password):
        security_logger.warning(
            "login_faile_invalid_password",
            user_id=user.id,
            email=email
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device = user_agent[:120] if user_agent else None
    
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "type": "access",
            "email": user.email
        }
    )

    refresh_token, jti = create_refresh_token(
        {
            "sub": str(user.id),
            "type": "refresh",
            "email": user.email
        }
    )
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    repository.create_refresh_token(
        db=db,
        user_id=user.id,
        jti_hash=hash_jti(jti),
        expires_at=expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    security_logger.info(
        "login_success",
        user_id=user.id,
        ip=ip_address,
        device=device
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
}

#Google OAuth access and refresh
def login_user_auth(db: Session, user, request):

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device = user_agent[:120] if user_agent else None

    access_token = create_access_token(
        {

            "sub": str(user.id),
            "type": "access",
            "email": user.email
        }
    )

    refresh_token, jti = create_refresh_token(
        {

            "sub": str(user.id),
            "type": "refresh",
            "email": user.email

        }
    )
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    repository.create_refresh_token(
        db=db,
        user_id=user.id,
        jti_hash=hash_jti(jti),
        expires_at=expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    security_logger.info(
        "oauth_login_success",
        user_id=user.id,
        ip=ip_address,
        device=device
    )

    return{
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def refresh_user_token(db: Session, refresh_token: str, request):
    
    logger.info("refresh_token_attempt")
    
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        logger.warning("refresh_token_invalid")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        logger.warning("refresh_token_wrong_type")
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    jti_hash = hash_jti(jti)

    stored_token = repository.get_refresh_token(db, jti_hash)

    if not stored_token:
        security_logger.warning(
            "refresh_token_revoked_or_missing",
            user_id=user_id
        )
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    # revoke old refresh token
    repository.revoke_refresh_token(db, jti_hash)

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device = user_agent[:120] if user_agent else None

    new_access_token = create_access_token(
        {
            "sub": user_id,
            "type": "access",
            "email": payload.get("email")
        }
    )

    new_refresh_token, new_jti = create_refresh_token(
        {
            "sub": user_id,
            "type": "refresh",
            "email": payload.get("email")
        }
    )

    new_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    repository.create_refresh_token(
        db=db,
        user_id=user_id,
        jti_hash=hash_jti(new_jti),
        expires_at=new_expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    logger.info(
        "refresh_token_success",
        user_id=user_id,
        ip=ip_address
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }

def logout(db: Session, refresh_token: str):
    
    logger.info("logout_attempt")
    
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
            )
    except JWTError:
        logger.warning("logout_invalid_token")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    if payload.get("type") != "refresh":
        logger.warning("logout_invalid_token_type")
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user_id = payload.get("sub")
    
    jti_hash = hash_jti(payload.get("jti"))

    stored_token = repository.get_refresh_token(db, jti_hash)

    if not stored_token:
        logger.warning(
            "logout_token_not_found",
            user_id=user_id
        )
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    repository.revoke_refresh_token(db, jti_hash)    
    
    return {"message": "Successfully logged out"}