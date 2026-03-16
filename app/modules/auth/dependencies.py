import uuid

import structlog
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.auth import repository
from app.modules.auth.models import User

settings = get_settings()

logger = structlog.get_logger()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    ip = request.client.host if request.client else "unknown"

    token = request.cookies.get("access_token")

    if not token:
        logger.warning("access_token_missing", ip_address=ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            logger.warning("invalid_token_type", ip_address=ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("token_missing_user_id", ip_address=ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except JWTError as err:
        logger.warning("invalid_or_expired_token", ip_address=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from err

    user = await repository.get_user_by_id(db, uuid.UUID(user_id))

    if user is None:
        logger.warning("user_not_found_for_token", user_id=user_id, ip_address=ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    logger.info("authenticated_user_access", user_id=user.id, ip_address=ip)

    return user
