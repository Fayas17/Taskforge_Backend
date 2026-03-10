from fastapi import HTTPException

from sqlalchemy.orm import Session

from jose import jwt, JWTError

from datetime import datetime, timedelta

from app.core.config import get_settings
from app.modules.auth import repository
from app.modules.auth.utils import hash_password, verify_password, hash_jti, create_access_token, create_refresh_token

settings = get_settings()

def register_user(db: Session, user_input):
    existing_user = repository.get_user_by_username(db, user_input.username)
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    existing_user = repository.get_user_by_email(db, user_input.email)
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user_input.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    user_data = {
        "username": user_input.username,
        "email": user_input.email,
        "hashed_password": hash_password(user_input.password),
    }

    return repository.create_user(db, user_data)

def login_user(db: Session, user_input, request):
    user = repository.get_user_by_email(db, user_input.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(user_input.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    device = user_agent
    
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

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
}

#Google OAuth access and refresh
def login_user_auth(db: Session, user, request):

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    device = user_agent

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

    return{
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def refresh_user_token(db: Session, refresh_token: str, request):
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    jti_hash = hash_jti(jti)

    stored_token = repository.get_refresh_token(db, jti_hash)

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    # revoke old refresh token
    repository.revoke_refresh_token(db, jti_hash)

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    device = user_agent

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

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }

def logout(db: Session, refresh_token: str):
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
            )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    jti_hash = hash_jti(payload.get("jti"))

    stored_token = repository.get_refresh_token(db, jti_hash)

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    repository.revoke_refresh_token(db, jti_hash)    
    
    return {"message": "Successfully logged out"}