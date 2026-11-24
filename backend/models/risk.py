"""
PI-EWS Risk Models.

Pydantic schemas for risk assessment results (not DB documents).
"""

from typing import List
from pydantic import BaseModel, Field


class RiskAssessment(BaseModel):
    """Result of a risk engine evaluation."""

    current_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Risk score after this turn",
    )
    previous_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Risk score before this turn",
    )
    delta: float = Field(
        default=0.0,
        description="Change in risk score",
    )
    level: str = Field(
        default="low",
        description="Risk level: low, medium, high, critical",
    )
    turn_number: int = 0
    contributing_factors: List[str] = Field(default_factory=list)
    recommendation: str = Field(
        default="allow",
        description="Recommended action: allow, monitor, restrict, block",
    )
