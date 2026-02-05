
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import config
import models
from database import get_db

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None: raise HTTPException(401, "Invalid token")
    except JWTError: raise HTTPException(401, "Invalid token")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None: raise HTTPException(401, "User not found")
    return user

def validate_password_strength(password: str) -> bool:
    """
    Enforce strict password policy:
    - At least 8 characters
    - At least 1 Uppercase
    - At least 1 Lowercase
    - At least 1 Digit
    - At least 1 Special Character
    """
    import re
    if len(password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must contain at least one special character")
    return True
