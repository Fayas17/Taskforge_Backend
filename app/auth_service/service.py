from http.client import HTTPException

from sqlalchemy.orm import Session

from app.auth_service import repository
from app.auth_service.utils import hash_password, verify_password, create_access_token

def register_user(db: Session, user_input):
    existing_user = repository.get_user_by_email(db, user_input.email)
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_user = repository.get_user_by_username(db, user_input.username)
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user_data = {
        "username": user_input.username,
        "email": user_input.email,
        "hashed_password": hash_password(user_input.password),
    }

    return repository.create_user(db, user_data)

def login_user(db: Session, user_input):
    user = repository.get_user_by_email(db, user_input.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(user_input.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email
        }
    )
    
    return access_token