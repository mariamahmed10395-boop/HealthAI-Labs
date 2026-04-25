# auth.py - Authentication routes and utilities

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
import requests

from db import (
    get_db, get_user_by_email, get_user_by_google_id, 
    create_user, update_user_last_login, get_user_by_id
)

# -------------------------
# Configuration
# -------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-use-openssl-rand-hex-32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# -------------------------
# Models
# -------------------------

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str  # expects ACCESS TOKEN

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    profile_picture: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

# -------------------------
# Helpers
# -------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_id(db, int(user_id))
    if not user:
        raise credentials_exception
    return user

# -------------------------
# Routes
# -------------------------

@auth_router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    user = get_user_by_email(db, user_data.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    user = create_user(
        db=db,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )

    access_token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile_picture": user.profile_picture,
            "is_verified": user.is_verified
        }
    }

@auth_router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(db, user_data.email)
    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    update_user_last_login(db, user.id)

    access_token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile_picture": user.profile_picture,
            "is_verified": user.is_verified
        }
    }

@auth_router.post("/google", response_model=Token)
def google_auth(auth_data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Accepts Google ACCESS TOKEN from frontend
    """

    try:
        # Get user info directly from Google
        google_user_info = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {auth_data.credential}"}
        ).json()

        if "sub" not in google_user_info:
            raise HTTPException(status_code=401, detail="Invalid Google token")

        google_id = google_user_info["sub"]
        email = google_user_info["email"]
        full_name = google_user_info.get("name")
        profile_picture = google_user_info.get("picture")

        user = get_user_by_google_id(db, google_id)

        if not user:
            user = get_user_by_email(db, email)
            if user:
                user.google_id = google_id
                user.oauth_provider = "google"
                user.profile_picture = profile_picture
                user.is_verified = True
                db.commit()
            else:
                user = create_user(
                    db=db,
                    email=email,
                    full_name=full_name,
                    google_id=google_id,
                    oauth_provider="google",
                    profile_picture=profile_picture
                )

        update_user_last_login(db, user.id)

        access_token = create_access_token({"sub": str(user.id)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "profile_picture": user.profile_picture,
                "is_verified": user.is_verified
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Google authentication failed: {str(e)}"
        )
