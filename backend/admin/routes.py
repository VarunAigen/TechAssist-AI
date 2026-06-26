"""Admin routes — tenant-scoped document management, analytics, user management."""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query as QueryParam
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func, update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import User, Document, Query, ChatSession, AuditLog
from database.audit import log_audit_action
from auth.jwt_handler import require_admin, get_current_user
from ingestion.parser import parse_document, get_file_type
from ingestion.chunker import chunk_text
from ingestion.embedder import store_chunks, delete_document_chunks, get_collection_stats
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Document Management ─────────────────────────────────────

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a document into the tenant's knowledge base."""
    tenant_id = current_user["tenant_id"]

    # Validate file type
    allowed_types = {".pdf", ".docx", ".md", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {allowed_types}")

    # Check tenant document limit
    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
    )
    doc_count = doc_count_result.scalar()

    # Read file content
    content = await file.read()

    # Validate file size
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(400, f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Save file to tenant-specific directory
    tenant_upload_dir = os.path.join(UPLOAD_DIR, tenant_id)
    os.makedirs(tenant_upload_dir, exist_ok=True)
    file_path = os.path.join(tenant_upload_dir, file.filename)

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # Parse document
        text = parse_document(file_path)
        if not text.strip():
            raise HTTPException(400, "Document appears to be empty")

        # Chunk text
        chunks = chunk_text(text)

        # Save to database
        doc = Document(
            tenant_id=tenant_id,
            filename=file.filename,
            original_name=file.filename,
            file_type=get_file_type(file.filename),
            file_size=len(content),
            chunk_count=len(chunks),
            uploaded_by=current_user["user_id"],
        )
        db.add(doc)
        await db.flush()

        # Embed and store chunks in tenant's collection
        stored = store_chunks(chunks, doc.id, file.filename, get_file_type(file.filename), tenant_id=tenant_id)

        # Audit log: document upload
        await log_audit_action(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            action="upload",
            resource_type="document",
            resource_id=doc.id,
            details={"filename": file.filename, "chunks": stored, "size": len(content)},
        )

        logger.info(
            f"Document '{file.filename}' ingested ({stored} chunks)",
            extra={"tenant_id": tenant_id, "user_id": current_user["user_id"]},
        )

        return {
            "message": f"Document '{file.filename}' ingested successfully",
            "doc_id": doc.id,
            "chunks_created": stored,
            "file_size": len(content),
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Ingestion failed: {e}", extra={"tenant_id": tenant_id})
        raise HTTPException(500, f"Ingestion failed: {str(e)}")


@router.get("/documents")
async def list_documents(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all documents in the tenant's knowledge base."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "original_name": doc.original_name,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "chunk_count": doc.chunk_count,
            "version": doc.version,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its chunks from the tenant's knowledge base."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.tenant_id == tenant_id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete from ChromaDB
    delete_document_chunks(doc_id, tenant_id=tenant_id)

    # Delete from database
    await db.delete(doc)

    # Delete file
    file_path = os.path.join(UPLOAD_DIR, tenant_id, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Audit log: document deletion
    await log_audit_action(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        action="delete",
        resource_type="document",
        resource_id=doc_id,
        details={"filename": doc.filename},
    )

    logger.info(
        f"Document '{doc.filename}' deleted",
        extra={"tenant_id": tenant_id, "user_id": current_user["user_id"]},
    )

    return {"message": f"Document '{doc.filename}' deleted successfully"}


# ── Analytics ────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get query analytics scoped to the tenant."""
    tenant_id = current_user["tenant_id"]

    # Total queries
    total_result = await db.execute(
        select(func.count(Query.id)).where(Query.tenant_id == tenant_id)
    )
    total = total_result.scalar()

    # Queries by confidence tier
    tier_result = await db.execute(
        select(Query.confidence_tier, func.count(Query.id))
        .where(Query.tenant_id == tenant_id)
        .group_by(Query.confidence_tier)
    )
    tier_counts = {row[0]: row[1] for row in tier_result.all()}

    # Recent queries
    recent_result = await db.execute(
        select(Query)
        .where(Query.tenant_id == tenant_id)
        .order_by(Query.created_at.desc())
        .limit(20)
    )
    recent = recent_result.scalars().all()

    # Document count
    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
    )
    doc_count = doc_count_result.scalar()

    # Average rating (excluding unrated)
    avg_result = await db.execute(
        select(func.avg(Query.rating))
        .where(Query.tenant_id == tenant_id, Query.rating != 0)
    )
    avg_rating = avg_result.scalar()

    # Average response time
    avg_time_result = await db.execute(
        select(func.avg(Query.response_time_ms))
        .where(Query.tenant_id == tenant_id, Query.response_time_ms.isnot(None))
    )
    avg_response_time = avg_time_result.scalar()

    # User count
    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id, User.is_active == True)
    )
    user_count = user_count_result.scalar()

    # ChromaDB stats for this tenant
    chroma_stats = get_collection_stats(tenant_id=tenant_id)

    return {
        "total_queries": total,
        "confidence_distribution": {
            "HIGH": tier_counts.get("HIGH", 0),
            "MEDIUM": tier_counts.get("MEDIUM", 0),
            "LOW": tier_counts.get("LOW", 0),
        },
        "total_documents": doc_count,
        "total_chunks": chroma_stats["total_chunks"],
        "total_users": user_count,
        "average_rating": round(avg_rating, 2) if avg_rating else None,
        "average_response_time_ms": round(avg_response_time, 0) if avg_response_time else None,
        "recent_queries": [
            {
                "id": q.id,
                "question": q.question,
                "confidence_tier": q.confidence_tier,
                "confidence_score": q.confidence_score,
                "rating": q.rating,
                "response_time_ms": q.response_time_ms,
                "is_resolved": q.is_resolved,
                "resolved_answer": q.resolved_answer,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in recent
        ],
    }


@router.get("/unanswered")
async def get_unanswered_queries(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get low-confidence queries — knowledge gaps for this tenant."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Query)
        .where(Query.tenant_id == tenant_id, Query.confidence_tier == "LOW")
        .order_by(Query.created_at.desc())
        .limit(50)
    )
    queries = result.scalars().all()

    return [
        {
            "id": q.id,
            "question": q.question,
            "confidence_score": q.confidence_score,
            "is_resolved": q.is_resolved,
            "resolved_answer": q.resolved_answer,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in queries
    ]


# ── User Management ─────────────────────────────────────────

class InviteUserRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "bd_rep"


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/users")
async def list_users(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the tenant."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users/invite")
async def invite_user(
    request: InviteUserRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Invite/create a new user in the tenant."""
    from auth.jwt_handler import hash_password
    from database.models import Tenant

    tenant_id = current_user["tenant_id"]

    # Check tenant user limit
    tenant = await db.get(Tenant, tenant_id)
    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id, User.is_active == True)
    )
    user_count = user_count_result.scalar()
    if user_count >= tenant.max_users:
        raise HTTPException(400, f"User limit reached ({tenant.max_users}). Upgrade your plan.")

    # Check duplicate email
    existing = await db.execute(
        select(User).where(User.email == request.email, User.tenant_id == tenant_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered in this organization")

    # Validate role
    valid_roles = ("bd_rep", "tenant_admin")
    role = request.role if request.role in valid_roles else "bd_rep"

    user = User(
        tenant_id=tenant_id,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=role,
    )
    db.add(user)
    await db.flush()

    # Audit log: user invited
    await log_audit_action(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        action="invite_user",
        resource_type="user",
        resource_id=user.id,
        details={"email": request.email, "role": role},
    )

    logger.info(
        f"User invited: {user.email} (role={role})",
        extra={"tenant_id": tenant_id, "user_id": current_user["user_id"]},
    )

    return {
        "message": f"User '{request.email}' created successfully",
        "user_id": user.id,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role or active status within the tenant."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Prevent self-demotion
    if user.id == current_user["user_id"] and request.role and request.role != user.role:
        raise HTTPException(400, "Cannot change your own role")

    if request.role is not None:
        valid_roles = ("bd_rep", "tenant_admin")
        if request.role in valid_roles:
            user.role = request.role

    if request.is_active is not None:
        # Prevent self-deactivation
        if user.id == current_user["user_id"] and not request.is_active:
            raise HTTPException(400, "Cannot deactivate your own account")
        user.is_active = request.is_active

    await db.flush()

    # Audit log: user updated
    changes = {}
    if request.role is not None:
        changes["role"] = request.role
    if request.is_active is not None:
        changes["is_active"] = request.is_active
    await log_audit_action(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        action="update_user",
        resource_type="user",
        resource_id=user_id,
        details={"email": user.email, "changes": changes},
    )

    logger.info(
        f"User updated: {user.email}",
        extra={"tenant_id": tenant_id, "user_id": current_user["user_id"]},
    )

    return {"message": f"User '{user.email}' updated successfully"}


@router.get("/audit-log")
async def list_audit_logs(
    page: int = 1,
    limit: int = 50,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated and filterable audit logs for the current tenant."""
    tenant_id = current_user["tenant_id"]

    # Calculate offset
    offset = (page - 1) * limit

    # Build query
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    query = query.order_by(AuditLog.created_at.desc())

    # Get total count for pagination
    count_query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if user_id:
        count_query = count_query.where(AuditLog.user_id == user_id)

    total_count_res = await db.execute(count_query)
    total_count = total_count_res.scalar()

    # Fetch log items
    result = await db.execute(query.offset(offset).limit(limit))
    logs = result.scalars().all()

    # Convert logs to JSON-serializable list
    log_items = []
    for l in logs:
        # Load user name if user exists
        user_name = "System"
        if l.user_id:
            u = await db.get(User, l.user_id)
            if u:
                user_name = u.full_name

        log_items.append({
            "id": l.id,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "user_name": user_name,
            "user_id": l.user_id,
        })

    return {
        "logs": log_items,
        "total": total_count,
        "page": page,
        "limit": limit,
    }


@router.get("/audit-log/export")
async def export_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Export audit logs as a downloadable CSV file."""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from datetime import datetime

    tenant_id = current_user["tenant_id"]

    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    query = query.order_by(AuditLog.created_at.desc())

    result = await db.execute(query)
    logs = result.scalars().all()

    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["ID", "Timestamp", "User ID", "User Name", "Action", "Resource Type", "Resource ID", "IP Address", "Details"])

    for l in logs:
        user_name = "System"
        if l.user_id:
            u = await db.get(User, l.user_id)
            if u:
                user_name = u.full_name
        writer.writerow([
            l.id,
            l.created_at.isoformat() if l.created_at else "",
            l.user_id or "",
            user_name,
            l.action,
            l.resource_type or "",
            l.resource_id or "",
            l.ip_address or "",
            str(l.details or {})
        ])

    output.seek(0)

    filename = f"audit_log_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ── Document Versioning ─────────────────────────────────────

@router.put("/documents/{doc_id}/replace")
async def replace_document(
    doc_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Replace a document with a new version (archives old chunks, ingests new)."""
    tenant_id = current_user["tenant_id"]

    # Find existing document
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.tenant_id == tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Read new file
    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(400, f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Save new file
    tenant_upload_dir = os.path.join(UPLOAD_DIR, tenant_id)
    os.makedirs(tenant_upload_dir, exist_ok=True)
    file_path = os.path.join(tenant_upload_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # Parse and chunk new document
        text = parse_document(file_path)
        if not text.strip():
            raise HTTPException(400, "New document appears to be empty")
        chunks = chunk_text(text)

        # Delete old chunks from ChromaDB
        delete_document_chunks(doc_id, tenant_id=tenant_id)

        # Update document record
        old_version = doc.version or 1
        doc.filename = file.filename
        doc.original_name = file.filename
        doc.file_type = get_file_type(file.filename)
        doc.file_size = len(content)
        doc.chunk_count = len(chunks)
        doc.version = old_version + 1
        doc.uploaded_by = current_user["user_id"]

        await db.flush()

        # Store new chunks
        stored = store_chunks(chunks, doc.id, file.filename, get_file_type(file.filename), tenant_id=tenant_id)

        # Audit log
        await log_audit_action(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            action="replace_document",
            resource_type="document",
            resource_id=doc.id,
            details={
                "filename": file.filename,
                "old_version": old_version,
                "new_version": doc.version,
                "chunks": stored,
            },
        )

        logger.info(
            f"Document '{file.filename}' replaced (v{old_version} → v{doc.version}, {stored} chunks)",
            extra={"tenant_id": tenant_id},
        )

        return {
            "message": f"Document updated to version {doc.version}",
            "doc_id": doc.id,
            "version": doc.version,
            "chunks_created": stored,
        }

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Document replace failed: {e}", extra={"tenant_id": tenant_id})
        raise HTTPException(500, f"Replace failed: {str(e)}")


# ── Feedback Loop (Low-Rated Queries) ────────────────────────

@router.get("/feedback/low-rated")
async def get_low_rated_queries(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get queries rated thumbs-down, grouped by topic — knowledge improvement opportunities."""
    tenant_id = current_user["tenant_id"]
    offset = (page - 1) * limit

    # Count
    count_result = await db.execute(
        select(func.count(Query.id)).where(
            Query.tenant_id == tenant_id,
            Query.rating == -1,
        )
    )
    total = count_result.scalar()

    # Fetch low-rated
    result = await db.execute(
        select(Query)
        .where(Query.tenant_id == tenant_id, Query.rating == -1)
        .order_by(Query.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    queries = result.scalars().all()

    return {
        "items": [
            {
                "id": q.id,
                "question": q.question,
                "answer": (q.answer[:200] + "...") if q.answer and len(q.answer) > 200 else q.answer,
                "confidence_tier": q.confidence_tier,
                "confidence_score": q.confidence_score,
                "is_bridge_response": q.is_bridge_response,
                "is_resolved": q.is_resolved,
                "resolved_answer": q.resolved_answer,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in queries
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/feedback/knowledge-gaps")
async def get_knowledge_gaps(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Identify knowledge gaps: low-confidence queries that suggest missing documentation."""
    tenant_id = current_user["tenant_id"]

    # Fetch low-confidence + bridge responses
    result = await db.execute(
        select(Query)
        .where(
            Query.tenant_id == tenant_id,
            or_(
                Query.confidence_tier == "LOW",
                Query.is_bridge_response == True,
            ),
        )
        .order_by(Query.created_at.desc())
        .limit(50)
    )
    queries = result.scalars().all()

    # Simple frequency analysis of question keywords
    topic_counts = {}
    for q in queries:
        # Extract key words (basic approach)
        words = q.question.lower().split()
        for word in words:
            if len(word) > 3 and word not in {"what", "when", "where", "which", "that", "this", "with", "from", "have", "does", "about", "your", "their", "there", "they", "them", "will", "would", "could", "should"}:
                topic_counts[word] = topic_counts.get(word, 0) + 1

    # Top 15 recurring topics
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        "total_gaps": len(queries),
        "top_topics": [{"keyword": k, "frequency": v} for k, v in top_topics],
        "recent_gaps": [
            {
                "id": q.id,
                "question": q.question,
                "confidence_tier": q.confidence_tier,
                "confidence_score": q.confidence_score,
                "is_bridge_response": q.is_bridge_response,
                "is_resolved": q.is_resolved,
                "resolved_answer": q.resolved_answer,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in queries[:10]
        ],
    }


# ── Document Search & Filter ────────────────────────────────

@router.get("/documents/search")
async def search_documents(
    q: str = "",
    file_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Search and filter documents with pagination."""
    tenant_id = current_user["tenant_id"]
    offset = (page - 1) * limit

    query = select(Document).where(Document.tenant_id == tenant_id)

    if q:
        query = query.where(Document.filename.ilike(f"%{q}%"))
    if file_type:
        query = query.where(Document.file_type == file_type)

    # Count
    from sqlalchemy import func as sa_func
    count_q = select(sa_func.count(Document.id)).where(Document.tenant_id == tenant_id)
    if q:
        count_q = count_q.where(Document.filename.ilike(f"%{q}%"))
    if file_type:
        count_q = count_q.where(Document.file_type == file_type)
    total_res = await db.execute(count_q)
    total = total_res.scalar()

    # Fetch
    result = await db.execute(
        query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    )
    docs = result.scalars().all()

    return {
        "items": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "original_name": doc.original_name,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "chunk_count": doc.chunk_count,
                "version": doc.version,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in docs
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


# ── Recent Queries with Filters ──────────────────────────────

@router.get("/queries")
async def list_queries(
    page: int = 1,
    limit: int = 20,
    confidence: Optional[str] = None,
    rated: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable list of all queries for the tenant."""
    tenant_id = current_user["tenant_id"]
    offset = (page - 1) * limit

    query = select(Query).where(Query.tenant_id == tenant_id)

    if confidence:
        query = query.where(Query.confidence_tier == confidence.upper())
    if rated == "positive":
        query = query.where(Query.rating == 1)
    elif rated == "negative":
        query = query.where(Query.rating == -1)
    elif rated == "unrated":
        query = query.where(Query.rating == 0)
    if search:
        query = query.where(Query.question.ilike(f"%{search}%"))

    # Count
    count_q = select(func.count(Query.id)).where(Query.tenant_id == tenant_id)
    if confidence:
        count_q = count_q.where(Query.confidence_tier == confidence.upper())
    if rated == "positive":
        count_q = count_q.where(Query.rating == 1)
    elif rated == "negative":
        count_q = count_q.where(Query.rating == -1)
    elif rated == "unrated":
        count_q = count_q.where(Query.rating == 0)
    if search:
        count_q = count_q.where(Query.question.ilike(f"%{search}%"))

    total_res = await db.execute(count_q)
    total = total_res.scalar()

    result = await db.execute(
        query.order_by(Query.created_at.desc()).offset(offset).limit(limit)
    )
    queries = result.scalars().all()

    return {
        "items": [
            {
                "id": q.id,
                "question": q.question,
                "answer": (q.answer[:200] + "...") if q.answer and len(q.answer) > 200 else q.answer,
                "confidence_tier": q.confidence_tier,
                "confidence_score": q.confidence_score,
                "rating": q.rating,
                "response_time_ms": q.response_time_ms,
                "is_bridge_response": q.is_bridge_response,
                "is_resolved": q.is_resolved,
                "resolved_answer": q.resolved_answer,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in queries
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


class ResolveQueryRequest(BaseModel):
    resolved_answer: str


@router.post("/queries/{query_id}/resolve")
async def resolve_query(
    query_id: int,
    request_body: ResolveQueryRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a low-confidence or unanswered query by appending its custom context to resolved_faq.txt and re-embedding."""
    tenant_id = current_user["tenant_id"]
    resolved_answer = request_body.resolved_answer.strip()

    if not resolved_answer:
        raise HTTPException(400, "Resolved answer cannot be empty")

    # Fetch the query and check ownership
    result = await db.execute(
        select(Query).where(Query.id == query_id, Query.tenant_id == tenant_id)
    )
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(404, "Query not found or does not belong to this tenant")

    # Append to resolved_faq.txt file
    tenant_upload_dir = os.path.join(UPLOAD_DIR, tenant_id)
    os.makedirs(tenant_upload_dir, exist_ok=True)
    faq_filename = "resolved_faq.txt"
    file_path = os.path.join(tenant_upload_dir, faq_filename)

    qa_entry = f"Question: {query.question}\nAnswer: {resolved_answer}\n---\n\n"

    try:
        # Append QA entry to resolved_faq.txt
        mode = "a" if os.path.exists(file_path) else "w"
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(qa_entry)

        # Parse and chunk updated resolved_faq.txt
        text = parse_document(file_path)
        chunks = chunk_text(text)

        # Query Document record in database
        doc_result = await db.execute(
            select(Document).where(Document.filename == faq_filename, Document.tenant_id == tenant_id)
        )
        doc = doc_result.scalar_one_or_none()

        if doc:
            # Delete old chunks from ChromaDB
            delete_document_chunks(doc.id, tenant_id=tenant_id)
            doc.chunk_count = len(chunks)
            doc.file_size = os.path.getsize(file_path)
            doc.version = (doc.version or 1) + 1
            doc.uploaded_by = current_user["user_id"]
        else:
            # Create a new Document entry
            doc = Document(
                tenant_id=tenant_id,
                filename=faq_filename,
                original_name=faq_filename,
                file_type="txt",
                file_size=os.path.getsize(file_path),
                chunk_count=len(chunks),
                version=1,
                uploaded_by=current_user["user_id"],
            )
            db.add(doc)

        await db.flush()

        # Re-embed and store chunks in ChromaDB
        stored = store_chunks(chunks, doc.id, faq_filename, "txt", tenant_id=tenant_id)

        # Update the query status in database
        query.is_resolved = True
        query.resolved_answer = resolved_answer
        await db.flush()

        # Audit log for resolution
        await log_audit_action(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            action="resolve_gap",
            resource_type="query",
            resource_id=query_id,
            details={"question": query.question, "resolved_chunks": stored},
        )

        logger.info(
            f"Query #{query_id} resolved with custom context added to '{faq_filename}'",
            extra={"tenant_id": tenant_id, "user_id": current_user["user_id"]},
        )

        return {
            "message": "Query resolved and added to knowledge base successfully",
            "query_id": query_id,
            "chunks_updated": stored,
        }

    except Exception as e:
        logger.error(f"Failed to resolve query/update knowledge: {e}", extra={"tenant_id": tenant_id})
        raise HTTPException(500, f"Resolution failed: {str(e)}")


