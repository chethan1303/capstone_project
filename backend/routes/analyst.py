"""Read-only investigation and report endpoints for analysts."""

import re
import smtplib
from datetime import datetime, timezone
from typing import List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from config import settings
from models.conversation import Conversation
from models.security_event import SecurityEvent
from models.user import User
from routes.admin import (
    analytics as admin_analytics,
    dashboard as admin_dashboard,
    get_conversation_detail as admin_conversation_detail,
    list_all_conversations as admin_list_conversations,
)
from services.auth_service import get_current_analyst_or_admin
from services.report_service import email_report

router = APIRouter(prefix="/api/analyst", tags=["analyst reports"])


async def _users_for_conversations(conversations):
    user_ids = {
        ObjectId(conversation.user_id)
        for conversation in conversations
        if isinstance(conversation.user_id, str)
        and ObjectId.is_valid(conversation.user_id)
    }
    if not user_ids:
        return {}

    users = await User.find({"_id": {"$in": list(user_ids)}}).to_list()
    return {str(user.id): user for user in users}


def _profile_details(user):
    if user is None:
        return None
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


def _conversation_summary(conversation):
    if conversation is None:
        return None
    return {
        "session_id": conversation.session_id,
        "status": conversation.status,
        "risk_level": conversation.risk_level,
        "current_risk_score": conversation.current_risk_score,
        "total_messages": conversation.total_messages,
        "detection_count": conversation.detection_count,
        "updated_at": conversation.updated_at.isoformat(),
    }


def _event_summary(event):
    return {
        "id": str(event.id),
        "session_id": event.session_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "details": event.details,
        "timestamp": event.timestamp.isoformat(),
    }


class EmailReportRequest(BaseModel):
    description: str = Field(min_length=5, max_length=2000)
    recipients: List[str] = Field(min_length=1, max_length=20)
    scope: Literal["conversation", "date_range"]
    session_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@router.get("/dashboard")
async def dashboard(analyst: User = Depends(get_current_analyst_or_admin)):
    return await admin_dashboard(analyst)


@router.get("/conversations")
async def list_conversations(
    status_filter: Optional[str] = Query(None, alias="status"),
    risk_level: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    analyst: User = Depends(get_current_analyst_or_admin),
):
    return await admin_list_conversations(
        status=status_filter,
        risk_level=risk_level,
        session_id=None,
        skip=skip,
        limit=limit,
        admin=analyst,
    )


@router.get("/conversations/{session_id}")
async def conversation_detail(
    session_id: str,
    analyst: User = Depends(get_current_analyst_or_admin),
):
    return await admin_conversation_detail(session_id, analyst)


@router.get("/security-events")
async def security_events(
    severity: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    analyst: User = Depends(get_current_analyst_or_admin),
):
    query = {"severity": severity} if severity else {}
    events = (
        await SecurityEvent.find(query)
        .sort("-timestamp")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    total = await SecurityEvent.find(query).count()
    session_ids = list(dict.fromkeys(event.session_id for event in events))
    conversations = (
        await Conversation.find({"session_id": {"$in": session_ids}}).to_list()
        if session_ids
        else []
    )
    conversations_by_session = {
        conversation.session_id: conversation for conversation in conversations
    }
    users_by_id = await _users_for_conversations(conversations)

    return {
        "total": total,
        "events": [
            {
                **_event_summary(event),
                "conversation": _conversation_summary(
                    conversations_by_session.get(event.session_id)
                ),
                "user_profile": _profile_details(
                    users_by_id.get(
                        conversations_by_session[event.session_id].user_id
                    )
                )
                if event.session_id in conversations_by_session
                else None,
            }
            for event in events
        ],
    }


@router.get("/flagged-conversations")
async def flagged_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    analyst: User = Depends(get_current_analyst_or_admin),
):
    query = {"status": "flagged"}
    conversations = (
        await Conversation.find(query)
        .sort("-updated_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    total = await Conversation.find(query).count()
    session_ids = [conversation.session_id for conversation in conversations]
    users_by_id = await _users_for_conversations(conversations)
    events = (
        await SecurityEvent.find({"session_id": {"$in": session_ids}})
        .sort("-timestamp")
        .limit(limit * 10)
        .to_list()
        if session_ids
        else []
    )
    recent_events_by_session = {}
    for event in events:
        session_events = recent_events_by_session.setdefault(event.session_id, [])
        if len(session_events) < 5:
            session_events.append(_event_summary(event))

    return {
        "total": total,
        "conversations": [
            {
                **_conversation_summary(conversation),
                "user_profile": _profile_details(
                    users_by_id.get(conversation.user_id)
                ),
                "recent_security_events": recent_events_by_session.get(
                    conversation.session_id, []
                ),
            }
            for conversation in conversations
        ],
    }


@router.get("/profiles")
async def recent_event_profiles(
    limit: int = Query(100, ge=1, le=200),
    analyst: User = Depends(get_current_analyst_or_admin),
):
    events = (
        await SecurityEvent.find_all()
        .sort("-timestamp")
        .limit(1000)
        .to_list()
    )
    session_ids = list(dict.fromkeys(event.session_id for event in events))
    conversations = (
        await Conversation.find({"session_id": {"$in": session_ids}}).to_list()
        if session_ids
        else []
    )
    conversations_by_session = {
        conversation.session_id: conversation for conversation in conversations
    }
    users_by_id = await _users_for_conversations(conversations)
    profiles = {}

    for event in events:
        conversation = conversations_by_session.get(event.session_id)
        if conversation is None:
            continue
        user = users_by_id.get(conversation.user_id)
        if user is None:
            continue
        profile_id = str(user.id)
        profile = profiles.get(profile_id)
        if profile is None:
            profile = {
                "user_profile": _profile_details(user),
                "latest_event": _event_summary(event),
                "latest_conversation": _conversation_summary(conversation),
                "security_event_count": 0,
            }
            profiles[profile_id] = profile
        profile["security_event_count"] += 1

    recent_profiles = list(profiles.values())[:limit]
    return {
        "total": len(profiles),
        "scanned_events": len(events),
        "profiles": recent_profiles,
    }


@router.get("/analytics")
async def analytics(analyst: User = Depends(get_current_analyst_or_admin)):
    return await admin_analytics(analyst)


@router.post("/reports/email", status_code=status.HTTP_202_ACCEPTED)
async def email_analysis_report(
    body: EmailReportRequest,
    analyst: User = Depends(get_current_analyst_or_admin),
):
    if not body.description.strip():
        raise HTTPException(status_code=422, detail="A report description is required")
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured. Set SMTP_HOST and SMTP_FROM in the backend environment.",
        )
    if settings.SMTP_USERNAME and not settings.SMTP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMTP authentication is incomplete. Set SMTP_PASSWORD in the backend environment.",
        )

    recipients = [recipient.strip() for recipient in body.recipients]
    if any(not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient) for recipient in recipients):
        raise HTTPException(status_code=422, detail="One or more recipient email addresses are invalid")
    recipients = list(dict.fromkeys(recipients))

    if body.scope == "conversation":
        if not body.session_id:
            raise HTTPException(status_code=422, detail="Select a conversation for this report")
        conversation = await Conversation.find_one(
            Conversation.session_id == body.session_id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversations = [conversation]
    else:
        if not body.start_date or not body.end_date:
            raise HTTPException(status_code=422, detail="Both report date boundaries are required")
        start = body.start_date
        end = body.end_date
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if start > end:
            raise HTTPException(status_code=422, detail="Start date must be before end date")

        conversations = await Conversation.find({
            "updated_at": {"$gte": start, "$lte": end},
        }).sort("-updated_at").limit(501).to_list()
        if len(conversations) > 500:
            raise HTTPException(
                status_code=422,
                detail="More than 500 conversations match. Narrow the date range before generating the report.",
            )
        if not conversations:
            raise HTTPException(status_code=404, detail="No conversations found in this date range")

    try:
        await email_report(recipients, body.description.strip(), conversations)
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Report email could not be sent. Check SMTP configuration and connectivity.",
        ) from exc

    return {
        "detail": "Report email sent",
        "recipient_count": len(recipients),
        "conversation_count": len(conversations),
        "sent_by": analyst.username,
    }
