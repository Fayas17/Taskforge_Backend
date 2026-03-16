from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.auth import repository
from app.modules.auth.models import User
from app.modules.auth.schemas import UserCreate, UserLogin
from app.modules.auth.utils import (
    create_access_token,
    create_refresh_token,
    hash_jti,
    hash_password,
    verify_password,
)

settings = get_settings()

logger = structlog.get_logger()
security_logger = structlog.get_logger("security")


async def register_user(db: AsyncSession, user_input: UserCreate) -> User:
    security_logger.info(
        "register_attempt",
        username=user_input.username,
        email=user_input.email,
    )

    existing_user = await repository.get_user_by_username(db, user_input.username)
    if existing_user:
        security_logger.warning("register_failed_username_taken", username=user_input.username)
        raise HTTPException(status_code=400, detail="Username already taken")

    existing_user = await repository.get_user_by_email(db, user_input.email)
    if existing_user:
        security_logger.warning("register_failed_email_taken", username=user_input.username)
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(user_input.password) < 8:
        security_logger.warning("register_failed_password_policy", email=user_input.email)
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    user_data = {
        "username": user_input.username,
        "email": user_input.email,
        "hashed_password": hash_password(user_input.password),
    }

    try:
        return await repository.create_user(db, user_data)
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already registered") from err


async def login_user(
    db: AsyncSession, user_input: UserLogin, ip_address: str, user_agent: str | None
) -> dict[str, str]:
    email = user_input.email

    security_logger.info("login_attempt", email=email)

    user = await repository.get_user_by_email(db, email)
    if not user:
        security_logger.warning("login_failed_user_not_found", email=email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # OAuth users have no password — reject local login attempts
    if not user.hashed_password or not verify_password(user_input.password, user.hashed_password):
        security_logger.warning("login_failed_invalid_password", user_id=user.id, email=email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return await _create_tokens(db, user, ip_address, user_agent, event="login_success")


async def login_user_auth(
    db: AsyncSession, user: User, ip_address: str, user_agent: str | None
) -> dict[str, str]:
    """OAuth variant of login — no password verification."""
    return await _create_tokens(db, user, ip_address, user_agent, event="oauth_login_success")


async def _create_tokens(
    db: AsyncSession,
    user: User,
    ip_address: str,
    user_agent: str | None,
    *,
    event: str,
) -> dict[str, str]:
    """Shared token creation logic for both local and OAuth login."""
    device = user_agent[:120] if user_agent else None

    access_token = create_access_token({"sub": str(user.id), "type": "access", "email": user.email})
    refresh_token, jti = create_refresh_token(
        {"sub": str(user.id), "type": "refresh", "email": user.email}
    )
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await repository.create_refresh_token(
        db=db,
        user_id=user.id,
        jti_hash=hash_jti(jti),
        expires_at=expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    security_logger.info(event, user_id=user.id, ip=ip_address, device=device)

    return {"access_token": access_token, "refresh_token": refresh_token}


async def refresh_user_token(
    db: AsyncSession, refresh_token: str, ip_address: str, user_agent: str | None
) -> dict[str, str]:
    logger.info("refresh_token_attempt")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as err:
        logger.warning("refresh_token_invalid")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from err

    if payload.get("type") != "refresh":
        logger.warning("refresh_token_wrong_type")
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti: str = payload.get("jti") or ""
    user_id: str = payload.get("sub") or ""
    jti_hash = hash_jti(jti)

    stored_token = await repository.get_refresh_token(db, jti_hash)
    if not stored_token:
        security_logger.warning("refresh_token_revoked_or_missing", user_id=user_id)
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    await repository.revoke_refresh_token(db, jti_hash)

    device = user_agent[:120] if user_agent else None

    new_access_token = create_access_token(
        {"sub": user_id, "type": "access", "email": payload.get("email")}
    )
    new_refresh_token, new_jti = create_refresh_token(
        {"sub": user_id, "type": "refresh", "email": payload.get("email")}
    )
    new_expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await repository.create_refresh_token(
        db=db,
        user_id=UUID(user_id),
        jti_hash=hash_jti(new_jti),
        expires_at=new_expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info("refresh_token_success", user_id=user_id, ip=ip_address)

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}


async def logout(db: AsyncSession, refresh_token: str) -> dict[str, str]:
    logger.info("logout_attempt")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as err:
        logger.warning("logout_invalid_token")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from err

    if payload.get("type") != "refresh":
        logger.warning("logout_invalid_token_type")
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id: str = payload.get("sub") or ""
    jti_hash = hash_jti(payload.get("jti") or "")

    stored_token = await repository.get_refresh_token(db, jti_hash)
    if not stored_token:
        logger.warning("logout_token_not_found", user_id=user_id)
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    await repository.revoke_refresh_token(db, jti_hash)

    return {"message": "Successfully logged out"}
