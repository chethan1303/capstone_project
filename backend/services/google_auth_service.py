"""Google ID-token verification and standard-user provisioning."""

import hashlib
import re
import secrets

from fastapi import HTTPException, status
from google.auth.exceptions import TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from config import settings
from models.user import User
from services.auth_service import hash_password


def _google_display_name(claims: dict, email: str) -> str:
    for key in ("name", "given_name"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:120]
    return email.split("@", 1)[0].replace(".", " ").replace("_", " ")[:120]


async def _sync_google_display_name(user: User, display_name: str) -> None:
    if user.display_name != display_name:
        user.display_name = display_name
        await user.save()


async def authenticate_google_credential(credential: str) -> User:
    """Verify Google's signed ID token and return an active standard user."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )

    try:
        claims = await run_in_threadpool(
            id_token.verify_oauth2_token,
            credential,
            GoogleRequest(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        ) from exc
    except TransportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google credential verification is temporarily unavailable",
        ) from exc

    subject = claims.get("sub")
    email = claims.get("email")
    if (
        not isinstance(subject, str)
        or not subject
        or not isinstance(email, str)
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        or claims.get("email_verified") is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account must provide a verified email address",
        )

    user = await User.find_one({"google_subject": subject})
    if user:
        if not user.is_active or user.role != "user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This account cannot sign in with Google",
            )
        await _sync_google_display_name(user, _google_display_name(claims, email))
        return user

    normalized_email = email.strip().lower()
    existing_email_user = await User.find_one({
        "email": {
            "$regex": f"^{re.escape(normalized_email)}$",
            "$options": "i",
        }
    })
    if existing_email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Sign in with that account instead.",
        )

    username = f"google_{hashlib.sha256(subject.encode('utf-8')).hexdigest()[:32]}"
    user = User(
        username=username,
        email=normalized_email,
        display_name=_google_display_name(claims, normalized_email),
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        role="user",
        google_subject=subject,
    )
    try:
        await user.insert()
    except DuplicateKeyError as exc:
        existing_google_user = await User.find_one({"google_subject": subject})
        if existing_google_user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not create the Google account. Please retry.",
            ) from exc
        if not existing_google_user.is_active or existing_google_user.role != "user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This account cannot sign in with Google",
            ) from exc
        await _sync_google_display_name(
            existing_google_user,
            _google_display_name(claims, normalized_email),
        )
        return existing_google_user
    return user
