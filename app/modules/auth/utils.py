import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return str(pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(pwd_context.verify(plain_password, hashed_password))


def hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM))


def create_refresh_token(data: dict) -> tuple[str, str]:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM))
    return encoded_jwt, jti
