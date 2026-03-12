import structlog

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth import repository
from app.core.config import get_settings

settings = get_settings()

security = HTTPBearer()

logger = structlog.get_logger()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    
    ip = request.client.host
    
    token = request.cookies.get("access_token")

    if not token:
        logger.warning(
            "access_token_missing",
            ip_address=ip
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            logger.warning(
                "invalid_token_type",
                ip_address=ip
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning(
                "token_missing_user_id",
                ip_address=ip
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    except JWTError:
        logger.warning(
            "invalid_or_expired_token",
            ip_address=ip
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    user = repository.get_user_by_id(db, user_id)

    if user is None:
        logger.warning(
            "user_not_found_for_token",
            user_id=user_id,
            ip_address=ip
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    logger.info(
        "authenticated_user_access",
        user_id=user.id,
        ip_address=ip
    )
    
    return user