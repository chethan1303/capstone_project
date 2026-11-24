"""Administrator-only account and role management."""

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from models.user import User
from services.auth_service import get_current_admin, hash_password

router = APIRouter(prefix="/api/admin/users", tags=["admin roles"])


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=72)
    role: Literal["user", "analyst", "admin"]


class UserRoleUpdateRequest(BaseModel):
    role: Literal["user", "analyst", "admin"]


class UserActiveUpdateRequest(BaseModel):
    is_active: bool


async def _count_active_administrators() -> int:
    """Include older account documents that predate the is_active field."""
    return await User.find({
        "role": "admin",
        "$or": [
            {"is_active": True},
            {"is_active": {"$exists": False}},
        ],
    }).count()


@router.get("")
async def list_users(admin: User = Depends(get_current_admin)):
    """List accounts without exposing password hashes."""
    users = await User.find_all().sort("-created_at").to_list()
    return [
        {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    admin: User = Depends(get_current_admin),
):
    """Create an account with an administrator-assigned role."""
    username = body.username.strip()
    email = body.email.strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username contains unsupported characters",
        )
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid email address is required",
        )
    if len(body.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at most 72 UTF-8 bytes",
        )
    if await User.find_one({"username": username}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    if await User.find_one({
        "email": {
            "$regex": f"^{re.escape(email)}$",
            "$options": "i",
        }
    }):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    await user.insert()
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.patch("/{username}/role")
async def update_user_role(
    username: str,
    body: UserRoleUpdateRequest,
    admin: User = Depends(get_current_admin),
):
    """Change a role while protecting the current and last active admin."""
    user = await User.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.username == admin.username and body.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot change your own administrator role",
        )
    if user.is_active and user.role == "admin" and body.role != "admin":
        active_admins = await _count_active_administrators()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote the last active administrator",
            )

    user.role = body.role
    await user.save()
    return {"username": user.username, "email": user.email, "role": user.role}


@router.delete("/{username}")
async def deactivate_user(
    username: str,
    admin: User = Depends(get_current_admin),
):
    """Deactivate an account without deleting its conversation or audit history."""
    user = await User.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.username == admin.username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate your own administrator account",
        )
    if user.is_active and user.role == "admin":
        active_admins = await _count_active_administrators()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot deactivate the last active administrator",
            )

    if user.is_active:
        user.is_active = False
        await user.save()
    return {
        "username": user.username,
        "is_active": user.is_active,
        "detail": "Account deactivated; conversation history was retained.",
    }


@router.patch("/{username}/active")
async def update_user_active(
    username: str,
    body: UserActiveUpdateRequest,
    admin: User = Depends(get_current_admin),
):
    """Reactivate an account or deactivate it with the same safety checks."""
    if body.is_active:
        user = await User.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.is_active:
            user.is_active = True
            await user.save()
        return {"username": user.username, "is_active": user.is_active}

    return await deactivate_user(username, admin)
