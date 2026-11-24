"""
PI-EWS Chat Route.

The core pipeline: receive message → detect → assess risk → defend → LLM → save.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

from models.user import User
from models.security_event import SecurityEvent
from engines.conversation_manager import ConversationManager
from engines.detection_engine import DetectionEngine
from engines.risk_engine import RiskEngine
from engines.defense_engine import DefenseEngine
from services.llm_service import get_llm_service
from services.auth_service import get_current_chat_user
from config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Instantiate engines (singletons for the app lifetime)
conversation_mgr = ConversationManager()
detection_engine = DetectionEngine()
risk_engine = RiskEngine()
defense_engine = DefenseEngine()


# ── Schemas ──────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10000)

    @field_validator("session_id", "message")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value


class MessageOut(BaseModel):
    role: str
    content: str
    timestamp: str
    detection_result: Optional[dict] = None
    risk_score_after: Optional[float] = None
    defense_action: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    risk_level: str
    risk_score: float
    turn_number: int
    defense_action: str
    is_suspicious: bool
    contributing_factors: List[str] = []
    detection_explanation: str = ""


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, user: User = Depends(get_current_chat_user)):
    """Main chat pipeline.

    1. Retrieve / create session
    2. Detection engine analysis
    3. Risk engine assessment
    4. Defense engine policy
    5. LLM response (or override)
    6. Persist everything
    7. Log security events
    """
    # 1. Session
    conversation = await conversation_mgr.get_or_create_session(
        session_id=body.session_id, user_id=str(user.id)
    )

    # 2. Detection
    detection_result = detection_engine.analyze(
        message=body.message,
        conversation_history=conversation.messages,
    )

    # 3. Risk assessment
    risk_assessment = risk_engine.assess(
        detection_result=detection_result,
        conversation=conversation,
    )

    # 4. Defense policy
    defense_policy = defense_engine.apply_policy(
        risk_assessment=risk_assessment,
        original_message=body.message,
    )

    # 5. Generate response
    if defense_policy.action == "block":
        bot_response = defense_policy.response_override
    else:
        # Build history for LLM
        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages
        ]
        history.append({"role": "user", "content": body.message})

        llm = get_llm_service()
        bot_response = await llm.generate_response(
            system_prompt=settings.HONEYPOT_SYSTEM_PROMPT,
            conversation_history=history,
            defense_additions=defense_policy.modified_system_prompt,
        )

    # 6. Persist user message + risk update + bot message
    conversation = await conversation_mgr.add_message(
        conversation=conversation,
        role="user",
        content=body.message,
        detection_signals=detection_result.signals,
        risk_score=risk_assessment.current_score,
        defense_action=defense_policy.action,
    )

    await conversation_mgr.update_risk(conversation, risk_assessment)

    conversation = await conversation_mgr.add_message(
        conversation=conversation,
        role="assistant",
        content=bot_response,
    )

    # 7. Log security event if warranted
    if detection_result.is_suspicious:
        severity_map = {
            "low": "info",
            "medium": "warning",
            "high": "high",
            "critical": "critical",
        }
        event = SecurityEvent(
            session_id=body.session_id,
            event_type="detection",
            severity=severity_map.get(risk_assessment.level, "info"),
            details={
                "detection_explanation": detection_result.explanation,
                "risk_score": risk_assessment.current_score,
                "risk_delta": risk_assessment.delta,
                "defense_action": defense_policy.action,
                "contributing_factors": risk_assessment.contributing_factors,
            },
        )
        await event.insert()

    return ChatResponse(
        response=bot_response,
        session_id=body.session_id,
        risk_level=risk_assessment.level,
        risk_score=risk_assessment.current_score,
        turn_number=risk_assessment.turn_number,
        defense_action=defense_policy.action,
        is_suspicious=detection_result.is_suspicious,
        contributing_factors=risk_assessment.contributing_factors,
        detection_explanation=detection_result.explanation,
    )


@router.get("/{session_id}/history")
async def get_history(session_id: str, user: User = Depends(get_current_chat_user)):
    """Get conversation history for a session."""
    conversation = await conversation_mgr.get_session_for_user(
        session_id=session_id,
        user_id=str(user.id),
    )
    messages = conversation.messages
    return [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
            "detection_result": m.detection_result.model_dump() if m.detection_result else None,
            "risk_score_after": m.risk_score_after,
            "defense_action": m.defense_action,
        }
        for m in messages
    ]
