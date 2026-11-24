"""Read-only investigation and report endpoints for analysts."""

import re
import smtplib
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from config import settings
from models.conversation import Conversation
from models.user import User
from routes.admin import (
    analytics as admin_analytics,
    dashboard as admin_dashboard,
    get_conversation_detail as admin_conversation_detail,
    list_all_conversations as admin_list_conversations,
    list_security_events as admin_list_events,
)
from services.auth_service import get_current_analyst_or_admin
from services.report_service import email_report

router = APIRouter(prefix="/api/analyst", tags=["analyst reports"])


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
    return await admin_list_events(severity=severity, skip=skip, limit=limit, admin=analyst)


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
