"""
PI-EWS Admin Routes.

Dashboard stats, conversation management, security events, and analytics
for admin users.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Literal, Optional
import re

from models.user import User
from models.conversation import Conversation
from models.security_event import SecurityEvent
from services.auth_service import get_current_admin, hash_password
from services.conversation_metrics import calculate_conversation_metrics

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def dashboard(admin: User = Depends(get_current_admin)):
    """Aggregate dashboard statistics."""
    total = await Conversation.count()
    active = await Conversation.find(Conversation.status == "active").count()
    flagged = await Conversation.find(Conversation.status == "flagged").count()
    blocked = await Conversation.find(Conversation.status == "blocked").count()

    all_convos = await Conversation.find_all().to_list()
    avg_risk = (
        sum(c.current_risk_score for c in all_convos) / len(all_convos)
        if all_convos
        else 0.0
    )

    recent_events = (
        await SecurityEvent.find_all()
        .sort("-timestamp")
        .limit(10)
        .to_list()
    )

    recent_convos = (
        await Conversation.find_all()
        .sort("-updated_at")
        .limit(10)
        .to_list()
    )

    return {
        "stats": {
            "total_conversations": total,
            "active_sessions": active,
            "flagged_sessions": flagged,
            "blocked_sessions": blocked,
            "average_risk_score": round(avg_risk, 4),
        },
        "recent_events": [
            {
                "id": str(e.id),
                "session_id": e.session_id,
                "event_type": e.event_type,
                "severity": e.severity,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in recent_events
        ],
        "recent_conversations": [
            {
                "session_id": c.session_id,
                "total_messages": c.total_messages,
                "risk_level": c.risk_level,
                "current_risk_score": c.current_risk_score,
                "status": c.status,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in recent_convos
        ],
    }


@router.get("/conversations")
async def list_all_conversations(
    status: Optional[Literal["active", "flagged", "blocked", "completed"]] = Query(None),
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = Query(None),
    session_id: Optional[str] = Query(None, min_length=1, max_length=128),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin),
):
    """List all conversations with optional filters."""
    query = {}
    if status:
        query["status"] = status
    if risk_level:
        query["risk_level"] = risk_level
    if session_id:
        query["session_id"] = {
            "$regex": re.escape(session_id.strip()),
            "$options": "i",
        }

    convos = (
        await Conversation.find(query)
        .sort("-updated_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    total = await Conversation.find(query).count()

    return {
        "total": total,
        "conversations": [
            {
                "session_id": c.session_id,
                "user_id": c.user_id,
                "total_messages": c.total_messages,
                "risk_level": c.risk_level,
                "current_risk_score": c.current_risk_score,
                "status": c.status,
                "user_deleted": c.user_deleted,
                "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
                "detection_count": c.detection_count,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                **asdict(calculate_conversation_metrics(c)),
            }
            for c in convos
        ],
    }


@router.get("/conversations/{session_id}")
async def get_conversation_detail(
    session_id: str, admin: User = Depends(get_current_admin)
):
    """Get full conversation detail including messages and risk timeline."""
    convo = await Conversation.find_one(Conversation.session_id == session_id)
    if not convo:
        from fastapi import HTTPException, status as st

        raise HTTPException(status_code=st.HTTP_404_NOT_FOUND, detail="Not found")

    events = (
        await SecurityEvent.find(SecurityEvent.session_id == session_id)
        .sort("-timestamp")
        .to_list()
    )

    metrics = calculate_conversation_metrics(convo)
    return {
        "session_id": convo.session_id,
        "user_id": convo.user_id,
        "status": convo.status,
        "risk_level": convo.risk_level,
        "current_risk_score": convo.current_risk_score,
        "user_deleted": convo.user_deleted,
        "deleted_at": convo.deleted_at.isoformat() if convo.deleted_at else None,
        "total_messages": convo.total_messages,
        "detection_count": convo.detection_count,
        "created_at": convo.created_at.isoformat(),
        "updated_at": convo.updated_at.isoformat(),
        **asdict(metrics),
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "detection_result": m.detection_result.model_dump() if m.detection_result else None,
                "risk_score_after": m.risk_score_after,
                "defense_action": m.defense_action,
                "prompt_tokens": m.prompt_tokens,
                "completion_tokens": m.completion_tokens,
                "message_text_bytes": len(m.content.encode("utf-8")),
            }
            for m in convo.messages
        ],
        "risk_scores": [
            {
                "turn_number": rs.turn_number,
                "score": rs.score,
                "level": rs.level,
                "timestamp": rs.timestamp.isoformat(),
                "contributing_signals": rs.contributing_signals,
            }
            for rs in convo.risk_scores
        ],
        "security_events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/security-events")
async def list_security_events(
    severity: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin),
):
    """List security events with optional severity filter."""
    query = {}
    if severity:
        query["severity"] = severity

    events = (
        await SecurityEvent.find(query)
        .sort("-timestamp")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    total = await SecurityEvent.find(query).count()

    return {
        "total": total,
        "events": [
            {
                "id": str(e.id),
                "session_id": e.session_id,
                "event_type": e.event_type,
                "severity": e.severity,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/analytics")
async def analytics(admin: User = Depends(get_current_admin)):
    """Provide analytics data for dashboard charts."""
    all_convos = await Conversation.find_all().to_list()

    # Risk distribution
    risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for c in all_convos:
        risk_dist[c.risk_level] = risk_dist.get(c.risk_level, 0) + 1

    # Status distribution
    status_dist = {"active": 0, "flagged": 0, "blocked": 0, "completed": 0}
    for c in all_convos:
        status_dist[c.status] = status_dist.get(c.status, 0) + 1

    # Detection rate
    total_msgs = sum(c.total_messages for c in all_convos)
    total_detections = sum(c.detection_count for c in all_convos)

    return {
        "risk_distribution": risk_dist,
        "status_distribution": status_dist,
        "total_messages": total_msgs,
        "total_detections": total_detections,
        "detection_rate": round(total_detections / max(total_msgs, 1), 4),
        "total_conversations": len(all_convos),
    }
