"""
PI-EWS Detection Models.

Pydantic schemas for detection signals and results (not DB documents).
"""

from typing import List
from pydantic import BaseModel, Field


class DetectionSignals(BaseModel):
    """Individual signals detected during message analysis."""

    injection_patterns: List[str] = Field(
        default_factory=list,
        description="List of matched injection pattern names",
    )
    role_manipulation: bool = False
    instruction_override: bool = False
    context_switching: bool = False
    encoding_attack: bool = False
    sentiment_shift: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Sentiment shift from previous turn (-1 to 1)",
    )
    similarity_to_known_attacks: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Similarity score to known attack templates",
    )
    message_anomaly_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Anomaly score based on message characteristics",
    )
    overall_suspicion: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Weighted aggregate suspicion score",
    )


class DetectionResult(BaseModel):
    """Complete result from the detection engine."""

    is_suspicious: bool = False
    signals: DetectionSignals = Field(default_factory=DetectionSignals)
    explanation: str = ""
