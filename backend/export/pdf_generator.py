"""PDF export — generate styled PDF from chat sessions."""

import io
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import Query, ChatSession, Tenant, User
from database.audit import log_audit_action
from auth.jwt_handler import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat Export"])


@router.get("/session/{session_id}/export")
async def export_session_pdf(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a chat session as a downloadable PDF."""
    tenant_id = current_user["tenant_id"]

    # Verify session belongs to user and tenant
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user["user_id"],
            ChatSession.tenant_id == tenant_id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # Load messages
    msg_result = await db.execute(
        select(Query)
        .where(Query.session_id == session_id, Query.tenant_id == tenant_id)
        .order_by(Query.created_at.asc())
    )
    messages = msg_result.scalars().all()

    if not messages:
        raise HTTPException(400, "Session has no messages to export")

    # Load tenant name
    tenant = await db.get(Tenant, tenant_id)
    tenant_name = tenant.name if tenant else "Unknown"

    # Generate PDF using reportlab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    except ImportError:
        raise HTTPException(500, "PDF generation library not installed. Run: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25 * mm,
        leftMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=HexColor('#7c3aed'),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#6b7280'),
        spaceAfter=16,
    )
    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        leftIndent=10,
        spaceAfter=6,
    )
    answer_style = ParagraphStyle(
        'Answer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#374151'),
        leftIndent=10,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        'Meta',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#9ca3af'),
        leftIndent=10,
        spaceAfter=12,
    )

    # Build document
    elements = []

    # Title
    elements.append(Paragraph(f"Chat Export — {tenant_name}", title_style))
    elements.append(Paragraph(
        f"Session: {session.title or 'Untitled'} | "
        f"Exported: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')} | "
        f"Messages: {len(messages)}",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e5e7eb')))
    elements.append(Spacer(1, 12))

    # Messages
    for i, msg in enumerate(messages):
        # Question
        elements.append(Paragraph(f"🧑 Q: {_escape_html(msg.question)}", question_style))

        # Answer (truncate very long answers for PDF)
        answer_text = msg.answer or "No response"
        if len(answer_text) > 3000:
            answer_text = answer_text[:3000] + "... [truncated]"
        elements.append(Paragraph(f"🤖 A: {_escape_html(answer_text)}", answer_style))

        # Metadata
        conf = msg.confidence_tier or "N/A"
        score = f"{msg.confidence_score:.1%}" if msg.confidence_score else "N/A"
        time_str = msg.created_at.strftime('%H:%M:%S') if msg.created_at else "N/A"
        rating = "👍" if msg.rating == 1 else ("👎" if msg.rating == -1 else "—")

        elements.append(Paragraph(
            f"Confidence: {conf} ({score}) | Rating: {rating} | Time: {time_str}",
            meta_style,
        ))

        if i < len(messages) - 1:
            elements.append(HRFlowable(width="80%", thickness=0.5, color=HexColor('#f3f4f6')))
            elements.append(Spacer(1, 6))

    doc.build(elements)
    buffer.seek(0)

    # Audit log
    await log_audit_action(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        action="export",
        resource_type="session",
        resource_id=session_id,
        details={"format": "pdf", "message_count": len(messages)},
    )

    filename = f"chat_export_{session_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _escape_html(text: str) -> str:
    """Escape HTML special characters for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "<br/>")
    )
