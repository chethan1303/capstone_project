"""
PI-EWS User Model.

Beanie document for user accounts with authentication data.
"""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class User(Document):
    """User account stored in MongoDB."""

    username: Indexed(str, unique=True)
    email: str
    display_name: Optional[str] = Field(default=None, max_length=120)
    hashed_password: str
    role: str = Field(default="user", description="'user', 'analyst', or 'admin'")
    google_subject: Optional[str] = None
    is_active: bool = Field(
        default=True,
        description="Whether this account can authenticate and access the application",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [
            IndexModel(
                [("google_subject", ASCENDING)],
                unique=True,
                partialFilterExpression={"google_subject": {"$type": "string"}},
            )
        ]
