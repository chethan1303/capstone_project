"""
PI-EWS Conversation Model.

Beanie document for conversations and embedded message / risk-snapshot models.
"""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field

from models.detection import DetectionSignals


# ── Embedded sub-models (NOT standalone documents) ──────────────────────────


class Message(BaseModel):
    """A single message within a conversation."""

    role: str = Field(description="'user' or 'assistant'")
    content: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    detection_result: Optional[DetectionSignals] = None
    risk_score_after: Optional[float] = None
    defense_action: Optional[str] = None
    prompt_tokens: Optional[int] = Field(default=None, ge=0)
    completion_tokens: Optional[int] = Field(default=None, ge=0)


class RiskSnapshot(BaseModel):
    """Point-in-time snapshot of the risk score for a conversation turn."""

    turn_number: int
    score: float
    level: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    contributing_signals: List[str] = Field(default_factory=list)


# ── Top-level document ──────────────────────────────────────────────────────


class Conversation(Document):
    """A conversation session stored in MongoDB."""

    user_id: Optional[str] = None
    session_id: Indexed(str, unique=True)
    messages: List[Message] = Field(default_factory=list)
    risk_scores: List[RiskSnapshot] = Field(default_factory=list)
    current_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: str = "low"
    status: str = Field(
        default="active",
        description="active | flagged | blocked | completed",
    )
    user_deleted: bool = False
    deleted_at: Optional[datetime] = None
    total_messages: int = 0
    detection_count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "conversations"
