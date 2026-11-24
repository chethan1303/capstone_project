"""
PI-EWS Security Event Model.

Beanie document for logging security events.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from beanie import Document, Indexed
from pydantic import Field


class SecurityEvent(Document):
    """An auditable security event stored in MongoDB."""

    session_id: Indexed(str)
    event_type: str = Field(
        description="detection | risk_escalation | defense_action | blocked"
    )
    severity: str = Field(
        description="info | warning | high | critical"
    )
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "security_events"
