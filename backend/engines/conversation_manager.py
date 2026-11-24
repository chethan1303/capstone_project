"""
PI-EWS Conversation Manager.

Manages conversation lifecycle — session creation, message storage,
and risk-score tracking in MongoDB via Beanie.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from models.conversation import Conversation, Message, RiskSnapshot
from models.detection import DetectionSignals
from models.risk import RiskAssessment


class ConversationManager:
    """High-level CRUD and state management for conversations."""

    async def get_or_create_session(
        self, session_id: str, user_id: str
    ) -> Conversation:
        """Retrieve an existing conversation or create a new one.

        Args:
            session_id: Unique session identifier.
            user_id: ID of the authenticated user.

        Returns:
            The Conversation document.
        """
        conversation = await Conversation.find_one(
            {"session_id": session_id}
        )
        if conversation is None:
            conversation = Conversation(
                session_id=session_id,
                user_id=user_id,
            )
            try:
                await conversation.insert()
            except DuplicateKeyError:
                conversation = await Conversation.find_one(
                    {"session_id": session_id}
                )
                if conversation is None:
                    raise

        if conversation.user_deleted or conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation

    async def get_session_for_user(
        self, session_id: str, user_id: str
    ) -> Conversation:
        """Return an existing visible session only to its owning user."""
        conversation = await Conversation.find_one(
            {"session_id": session_id}
        )
        if (
            conversation is None
            or conversation.user_deleted
            or conversation.user_id != user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation

    async def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        detection_signals: Optional[DetectionSignals] = None,
        risk_score: Optional[float] = None,
        defense_action: Optional[str] = None,
    ) -> Conversation:
        """Append a message to the conversation and persist.

        Args:
            conversation: The conversation document.
            role: 'user' or 'assistant'.
            content: Message text.
            detection_signals: Signals from the detection engine (user msgs).
            risk_score: Risk score after this message.
            defense_action: Defense action applied (user msgs).

        Returns:
            The updated Conversation document.
        """
        msg = Message(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
            detection_result=detection_signals,
            risk_score_after=risk_score,
            defense_action=defense_action,
        )
        conversation.messages.append(msg)
        conversation.total_messages += 1
        conversation.updated_at = datetime.now(timezone.utc)

        if detection_signals and detection_signals.overall_suspicion >= 0.35:
            conversation.detection_count += 1

        await conversation.save()
        return conversation

    async def update_risk(
        self,
        conversation: Conversation,
        risk_assessment: RiskAssessment,
    ) -> Conversation:
        """Update the conversation's risk score and append a snapshot.

        Args:
            conversation: The conversation document.
            risk_assessment: The risk engine's assessment.

        Returns:
            The updated Conversation document.
        """
        conversation.current_risk_score = risk_assessment.current_score
        conversation.risk_level = risk_assessment.level

        snapshot = RiskSnapshot(
            turn_number=risk_assessment.turn_number,
            score=risk_assessment.current_score,
            level=risk_assessment.level,
            timestamp=datetime.now(timezone.utc),
            contributing_signals=risk_assessment.contributing_factors,
        )
        conversation.risk_scores.append(snapshot)

        # Update conversation status based on risk
        if risk_assessment.level == "critical":
            conversation.status = "blocked"
        elif risk_assessment.level == "high":
            conversation.status = "flagged"

        conversation.updated_at = datetime.now(timezone.utc)
        await conversation.save()
        return conversation

    async def get_user_conversations(
        self, user_id: str
    ) -> List[Conversation]:
        """Get all conversations for a specific user."""
        return await Conversation.find(
            Conversation.user_id == user_id
        ).sort("-updated_at").to_list()

    async def get_all_conversations(
        self,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Conversation]:
        """Get conversations with optional filters (admin use)."""
        query = {}
        if status:
            query["status"] = status
        if risk_level:
            query["risk_level"] = risk_level

        return (
            await Conversation.find(query)
            .sort("-updated_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )
