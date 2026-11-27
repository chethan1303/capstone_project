"""Build and email PDF/CSV reports for analyst investigations."""

import asyncio
import csv
import io
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import settings
from models.conversation import Conversation
from services.conversation_metrics import calculate_conversation_metrics


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def build_csv(conversations: List[Conversation]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "session_id",
        "user_id",
        "conversation_status",
        "risk_level",
        "current_risk_score",
        "detection_count",
        "total_messages",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "token_usage_complete",
        "message_text_bytes",
        "role",
        "message_timestamp",
        "message_content",
        "message_risk_score",
        "defense_action",
        "detection_signals",
        "message_prompt_tokens",
        "message_completion_tokens",
        "message_text_bytes",
    ])
    for conversation in conversations:
        metrics = calculate_conversation_metrics(conversation)
        session_metrics = [
            metrics.prompt_tokens,
            metrics.completion_tokens,
            metrics.total_tokens,
            metrics.token_usage_complete,
            metrics.message_text_bytes,
        ]
        if not conversation.messages:
            writer.writerow([
                _csv_safe(conversation.session_id),
                _csv_safe(conversation.user_id),
                _csv_safe(conversation.status),
                _csv_safe(conversation.risk_level),
                conversation.current_risk_score,
                conversation.detection_count,
                conversation.total_messages,
                *session_metrics,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ])
            continue
        for message in conversation.messages:
            signals = message.detection_result.model_dump() if message.detection_result else {}
            writer.writerow([
                _csv_safe(conversation.session_id),
                _csv_safe(conversation.user_id),
                _csv_safe(conversation.status),
                _csv_safe(conversation.risk_level),
                conversation.current_risk_score,
                conversation.detection_count,
                conversation.total_messages,
                *session_metrics,
                _csv_safe(message.role),
                message.timestamp.isoformat(),
                _csv_safe(message.content),
                message.risk_score_after,
                _csv_safe(message.defense_action),
                _csv_safe(str(signals)),
                message.prompt_tokens,
                message.completion_tokens,
                len(message.content.encode("utf-8")),
            ])
    return output.getvalue().encode("utf-8-sig")


def build_pdf(description: str, conversations: List[Conversation]) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    metrics_by_conversation = [
        calculate_conversation_metrics(conversation)
        for conversation in conversations
    ]
    complete_token_sessions = [
        metrics.total_tokens
        for metrics in metrics_by_conversation
        if metrics.token_usage_complete
    ]
    total_message_text_bytes = sum(
        metrics.message_text_bytes for metrics in metrics_by_conversation
    )
    story = [
        Paragraph("PI-EWS Security Analysis Report", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"<b>Report description:</b> {escape(description)}", styles["BodyText"]),
        Paragraph(
            f"<b>Generated:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["BodyText"],
        ),
        Paragraph(f"<b>Conversations:</b> {len(conversations)}", styles["BodyText"]),
        Paragraph(
            "<b>Provider-reported LLM tokens:</b> "
            f"{sum(complete_token_sessions):,} across "
            f"{len(complete_token_sessions)} fully tracked conversation(s)",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Message text size:</b> {total_message_text_bytes:,} bytes",
            styles["BodyText"],
        ),
        Spacer(1, 14),
    ]

    table_data = [[
        "Session",
        "Risk",
        "Score",
        "Detections",
        "Messages",
        "LLM tokens",
        "Text KB",
        "Status",
    ]]
    for conversation, metrics in zip(conversations, metrics_by_conversation):
        table_data.append([
            Paragraph(escape(conversation.session_id), styles["BodyText"]),
            escape(conversation.risk_level),
            f"{conversation.current_risk_score:.3f}",
            str(conversation.detection_count),
            str(conversation.total_messages),
            str(metrics.total_tokens) if metrics.token_usage_complete else "Not tracked",
            f"{metrics.message_text_bytes / 1024:.1f}",
            escape(conversation.status),
        ])

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            1.65 * inch,
            0.55 * inch,
            0.55 * inch,
            0.65 * inch,
            0.55 * inch,
            0.75 * inch,
            0.55 * inch,
            0.75 * inch,
        ],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18382d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aab7b1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f0")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    document.build(story)
    return output.getvalue()


def _send_email(recipients: List[str], description: str, pdf: bytes, csv_data: bytes) -> None:
    message = EmailMessage()
    message["Subject"] = "PI-EWS security analysis report"
    message["From"] = settings.SMTP_FROM
    message["To"] = ", ".join(recipients)
    message.set_content(
        f"An analyst has prepared a PI-EWS security report.\n\n"
        f"Description: {description}\n"
        "The PDF summary and CSV analysis data are attached."
    )
    message.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename="piews-analysis-report.pdf",
    )
    message.add_attachment(
        csv_data,
        maintype="text",
        subtype="csv",
        filename="piews-analysis-data.csv",
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        server.ehlo()
        if settings.SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)


async def email_report(
    recipients: List[str],
    description: str,
    conversations: List[Conversation],
) -> None:
    pdf = build_pdf(description, conversations)
    csv_data = build_csv(conversations)
    await asyncio.to_thread(_send_email, recipients, description, pdf, csv_data)
