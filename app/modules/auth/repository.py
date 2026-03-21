from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RefreshToken, User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: dict) -> User:
    user = User(**user_data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_refresh_token(
    db: AsyncSession,
    user_id: UUID,
    jti_hash: str,
    expires_at: datetime,
    device: str | None,
    ip_address: str,
    user_agent: str | None,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        jti_hash=jti_hash,
        expires_at=expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return refresh_token


async def get_refresh_token(db: AsyncSession, jti_hash: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.jti_hash == jti_hash,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, jti_hash: str) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.jti_hash == jti_hash,
            RefreshToken.is_revoked.is_(False),
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.is_revoked = True
        await db.commit()
