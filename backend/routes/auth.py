"""
PI-EWS Auth Routes.

Registration, login (JWT), and profile endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from pymongo.errors import DuplicateKeyError
import re

from models.user import User
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from services.google_auth_service import authenticate_google_credential

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / response schemas ──────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", value):
            raise ValueError("Username contains unsupported characters")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot be blank")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    email: str
    role: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest):
    """Register a new user account."""
    existing = await User.find_one(User.username == body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    existing = await User.find_one({
        "email": {
            "$regex": f"^{re.escape(body.email)}$",
            "$options": "i",
        }
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    try:
        await user.insert()
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        ) from exc
    return UserResponse(username=user.username, email=user.email, role=user.role)


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate a standard user and return a JWT access token."""
    return await _login(form, required_role="user")


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate an administrator."""
    return await _login(form, required_role="admin")


@router.post("/analyst/login", response_model=TokenResponse)
async def analyst_login(form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate an analyst."""
    return await _login(form, required_role="analyst")


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleLoginRequest):
    """Verify a Google ID token and sign in a standard user account."""
    user = await authenticate_google_credential(body.credential)
    if user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google sign-in is available only for standard user accounts",
        )
    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


async def _login(form: OAuth2PasswordRequestForm, required_role: str) -> TokenResponse:
    """Validate credentials and ensure the account belongs to the selected portal."""
    if not form.username.strip() or len(form.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials for this sign-in portal",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await User.find_one({"username": form.username})
    if (
        not user
        or not user.is_active
        or user.role != required_role
        or not verify_password(form.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials for this sign-in portal",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(username=user.username, email=user.email, role=user.role)
