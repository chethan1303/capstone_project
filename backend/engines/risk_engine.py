"""
PI-EWS Risk Engine.

Implements dynamic, cumulative risk scoring using an exponential weighted
moving average (EWMA) with configurable sensitivity and decay.
"""

from typing import List

from models.detection import DetectionResult
from models.conversation import Conversation
from models.risk import RiskAssessment


def _classify_level(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def _level_to_recommendation(level: str) -> str:
    return {
        "low": "allow",
        "medium": "monitor",
        "high": "restrict",
        "critical": "block",
    }.get(level, "allow")


class RiskEngine:
    """Calculates a dynamic, cumulative risk score across conversation turns.

    The score uses an EWMA so that recent suspicious activity weighs more,
    but history still matters.  Benign turns slowly decay the score, ensuring
    that occasional normal messages don't instantly clear the slate.
    """

    def __init__(self, alpha: float = 0.3, decay: float = 0.05):
        """
        Args:
            alpha: Sensitivity factor for EWMA (0–1). Higher = more reactive.
            decay: Amount to subtract for a benign message (clamped ≥ 0).
        """
        self.alpha = alpha
        self.decay = decay

    def assess(
        self,
        detection_result: DetectionResult,
        conversation: Conversation,
    ) -> RiskAssessment:
        """Evaluate risk based on the latest detection and conversation history.

        Args:
            detection_result: Output from the detection engine.
            conversation: The full conversation document.

        Returns:
            RiskAssessment with score, level, and recommendation.
        """
        previous_score = conversation.current_risk_score
        detection_score = detection_result.signals.overall_suspicion

        # EWMA update
        if detection_result.is_suspicious:
            new_score = self.alpha * detection_score + (1 - self.alpha) * previous_score
            # Ensure score only goes *up* when detection is positive
            new_score = max(new_score, previous_score)
        else:
            # Slow decay for benign messages
            new_score = max(previous_score - self.decay, 0.0)

        new_score = round(min(new_score, 1.0), 4)
        delta = round(new_score - previous_score, 4)
        level = _classify_level(new_score)

        # Build contributing factors list for explainability
        factors: List[str] = []
        signals = detection_result.signals
        if signals.injection_patterns:
            factors.append(f"Injection patterns: {', '.join(signals.injection_patterns)}")
        if signals.role_manipulation:
            factors.append("Role manipulation")
        if signals.instruction_override:
            factors.append("Instruction override")
        if signals.context_switching:
            factors.append("Context switching")
        if signals.encoding_attack:
            factors.append("Encoding attack")
        if signals.similarity_to_known_attacks > 0.4:
            factors.append(f"Attack similarity: {signals.similarity_to_known_attacks:.0%}")
        if not detection_result.is_suspicious and delta < 0:
            factors.append("Decay (benign message)")

        turn_number = len([m for m in conversation.messages if m.role == "user"]) + 1

        return RiskAssessment(
            current_score=new_score,
            previous_score=previous_score,
            delta=delta,
            level=level,
            turn_number=turn_number,
            contributing_factors=factors,
            recommendation=_level_to_recommendation(level),
        )
