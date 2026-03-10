from datetime import datetime

from sqlalchemy.orm import Session
from .models import User, RefreshToken
from uuid import UUID


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user_data: dict):
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_refresh_token(db: Session, user_id: UUID, jti_hash: str, expires_at, device, ip_address, user_agent):
    refresh_token = RefreshToken(
        user_id=user_id,
        jti_hash=jti_hash,
        expires_at=expires_at,
        device=device,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token

def get_refresh_token(db: Session, jti_hash: str):
    return db.query(RefreshToken).filter(
        RefreshToken.jti_hash == jti_hash,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
        ).first()

def revoke_refresh_token(db: Session, jti_hash: str):    
    token = db.query(RefreshToken).filter(RefreshToken.jti_hash == jti_hash, RefreshToken.is_revoked == False).first()
    if token:
        token.is_revoked = True
        db.commit()