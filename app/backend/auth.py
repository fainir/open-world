import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import bcrypt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models import User

SECRET_KEY = os.environ.get("JWT_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72

security = HTTPBearer(auto_error=False)


# ── Pydantic schemas ──

class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=10, max_length=72)

    @field_validator('password')
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must fit within 72 UTF-8 bytes')
        return value


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: str
    email: str
    username: str


# ── Helpers ──

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8')[:72], hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, revision: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire, "rev": revision}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Dependencies ──

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        if not user or payload.get('rev', 0) != user.auth_revision:
            return None
        return user
    except jwt.PyJWTError:
        return None


def get_current_user_required(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


# ── Route handlers ──

def signup(req: SignupRequest, db: Session) -> TokenResponse:
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(req.username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")

    user = User(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.auth_revision)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "username": user.username},
    )


def login(req: LoginRequest, db: Session) -> TokenResponse:
    user = db.query(User).filter(
        (User.email == req.login) | (User.username == req.login)
    ).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id, user.auth_revision)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "username": user.username},
    )
