"""
PI-EWS Conversations Routes.

User-facing CRUD for their own conversations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from models.user import User
from models.conversation import Conversation
from services.auth_service import get_current_chat_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(user: User = Depends(get_current_chat_user)):
    """List the authenticated user's conversations."""
    convos = (
        await Conversation.find({
            "user_id": str(user.id),
            "user_deleted": {"$ne": True},
        })
        .sort("-updated_at")
        .to_list()
    )
    return [
        {
            "session_id": c.session_id,
            "total_messages": c.total_messages,
            "risk_level": c.risk_level,
            "status": c.status,
            "current_risk_score": c.current_risk_score,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in convos
    ]


@router.get("/{session_id}")
async def get_conversation(session_id: str, user: User = Depends(get_current_chat_user)):
    """Get a specific conversation."""
    convo = await Conversation.find_one(Conversation.session_id == session_id)
    if not convo or convo.user_id != str(user.id) or convo.user_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return convo.model_dump()


@router.delete("/{session_id}")
async def delete_conversation(session_id: str, user: User = Depends(get_current_chat_user)):
    """Hide a conversation from its owner without removing stored analysis."""
    convo = await Conversation.find_one(Conversation.session_id == session_id)
    if not convo or convo.user_id != str(user.id) or convo.user_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    convo.user_deleted = True
    convo.deleted_at = datetime.now(timezone.utc)
    await convo.save()
    return {"detail": "Conversation hidden from your history"}
