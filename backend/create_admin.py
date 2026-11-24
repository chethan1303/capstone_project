"""Interactively bootstrap the first administrator account."""

import asyncio
import getpass
import re

from pymongo.errors import DuplicateKeyError

from database import init_db
from models.user import User
from services.auth_service import hash_password


def validate_admin_input(
    username: str, email: str, password: str, confirmation: str
) -> tuple[str, str]:
    username = username.strip()
    email = email.strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", username):
        raise ValueError("Username must be 3-50 letters, numbers, '.', '_' or '-'.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 12 or not password.strip():
        raise ValueError("Password must contain at least 12 non-blank characters.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes.")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return username, email


async def create_first_admin(
    username: str, email: str, password: str, confirmation: str
) -> User:
    """Create one initial admin; use the authenticated admin API for later accounts."""
    username, email = validate_admin_input(username, email, password, confirmation)
    bootstrap_collection = User.get_motor_collection().database["admin_bootstrap"]
    try:
        await bootstrap_collection.insert_one({"_id": "initial-administrator"})
    except DuplicateKeyError as exc:
        raise ValueError("Administrator bootstrap has already been completed.") from exc

    try:
        if await User.find(User.role == "admin").count():
            raise ValueError("An administrator already exists; bootstrap is disabled.")
        if await User.find_one(User.username == username):
            raise ValueError("That username already exists.")
        if await User.find_one({
            "email": {
                "$regex": f"^{re.escape(email)}$",
                "$options": "i",
            }
        }):
            raise ValueError("That email already exists.")

        admin = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
        )
        await admin.insert()
    except Exception:
        await bootstrap_collection.delete_one({"_id": "initial-administrator"})
        raise
    return admin


async def main():
    await init_db()
    username = input("Admin username: ")
    email = input("Admin email: ")
    password = getpass.getpass("Admin password (at least 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")

    try:
        await create_first_admin(username, email, password, confirmation)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print("Initial administrator account created.")


if __name__ == "__main__":
    asyncio.run(main())
