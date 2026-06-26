"""FastAPI main application — Multi-tenant RAG Knowledge Assistant."""

import os
import json
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from config import settings
from logging_config import setup_logging
from database.session import init_db, close_db, get_db, get_db_context
from database.models import User, Tenant, Query, ChatSession, Document
from auth.routes import router as auth_router
from auth.jwt_handler import get_current_user
from admin.routes import router as admin_router
from admin.superadmin_routes import router as superadmin_router
from export.pdf_generator import router as export_router
from query.formatter import process_query
from ingestion.parser import parse_document
from ingestion.chunker import chunk_text
from ingestion.embedder import store_chunks

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


# ── Rate Limiter Setup ───────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)


# ── Startup / Shutdown ───────────────────────────────────────

async def seed_default_tenant():
    """Create a default tenant and demo users for development."""
    from auth.jwt_handler import hash_password

    async with get_db_context() as db:
        # Check if any tenant exists
        result = await db.execute(select(Tenant).limit(1))
        if result.scalar_one_or_none():
            logger.info("Tenants already exist, skipping seed")
            return

        # Create default tenant (CloudNexus demo)
        tenant = Tenant(
            name="CloudNexus",
            slug="cloudnexus",
            plan="enterprise",
            max_documents=100,
            max_users=50,
        )
        db.add(tenant)
        await db.flush()

        # Create demo users
        demo_users = [
            ("demo@cloudnexus.com", hash_password("demo123"), "Alex Morgan", "bd_rep"),
            ("admin@cloudnexus.com", hash_password("admin123"), "Sam Chen", "tenant_admin"),
            ("super@cloudnexus.com", hash_password("super123"), "Super Admin", "super_admin"),
        ]

        for email, pwd_hash, name, role in demo_users:
            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=pwd_hash,
                full_name=name,
                role=role,
            )
            db.add(user)

        await db.flush()
        logger.info(f"Default tenant '{tenant.name}' created with {len(demo_users)} demo users (tenant_id={tenant.id})")

        # Auto-ingest knowledge base documents for default tenant
        await _ingest_knowledge_base(db, tenant.id)


async def _ingest_knowledge_base(db: AsyncSession, tenant_id: str):
    """Auto-ingest documents from the knowledge_base directory for a tenant."""
    kb_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")
    if not os.path.exists(kb_dir):
        logger.warning("No knowledge_base directory found, skipping auto-ingestion")
        return

    # Check which files are already ingested for this tenant
    result = await db.execute(
        select(Document.filename).where(Document.tenant_id == tenant_id)
    )
    existing = {row[0] for row in result.all()}

    ingested = 0
    for filename in os.listdir(kb_dir):
        if filename.startswith(".") or filename.startswith("_"):
            continue
        if filename in existing:
            continue

        file_path = os.path.join(kb_dir, filename)
        if not os.path.isfile(file_path):
            continue

        try:
            text = parse_document(file_path)
            chunks = chunk_text(text)

            doc = Document(
                tenant_id=tenant_id,
                filename=filename,
                original_name=filename,
                file_type=filename.split(".")[-1],
                file_size=os.path.getsize(file_path),
                chunk_count=len(chunks),
                uploaded_by=None,
            )
            db.add(doc)
            await db.flush()

            store_chunks(chunks, doc.id, filename, filename.split(".")[-1], tenant_id=tenant_id)
            ingested += 1
            logger.info(f"Ingested: {filename} ({len(chunks)} chunks)")

        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}")

    if ingested:
        logger.info(f"Auto-ingested {ingested} documents for tenant {tenant_id}")
    else:
        logger.info("All knowledge_base documents already ingested")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    setup_logging(settings.ENVIRONMENT)
    logger.info("Starting TechAssist AI (Multi-Tenant RAG Knowledge Assistant)...")

    # Validate config in production
    if settings.ENVIRONMENT == "prod":
        settings.validate()

    # Initialize database
    await init_db()
    await seed_default_tenant()

    logger.info("Application ready!")
    yield

    # Shutdown
    await close_db()
    logger.info("Application shutdown complete")


# ── App Factory ──────────────────────────────────────────────

app = FastAPI(
    title="TechAssist AI — Multi-Tenant RAG Knowledge Assistant",
    description="A multi-tenant Retrieval-Augmented Generation assistant for business development teams",
    version="2.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
allowed_origins = [settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"]
if settings.ENVIRONMENT == "prod":
    allowed_origins = [settings.FRONTEND_URL]  # Restrict in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(superadmin_router)
app.include_router(export_router)


# ── Chat Endpoints ───────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[int] = None


class RatingRequest(BaseModel):
    rating: int  # 1 (thumbs up) or -1 (thumbs down)


@app.post("/api/chat")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat(
    request_body: ChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Main chat endpoint — processes a question through the tenant's RAG pipeline."""
    question = request_body.question.strip()

    if not question:
        raise HTTPException(400, "Question cannot be empty")

    if len(question) > settings.MAX_QUESTION_LENGTH:
        raise HTTPException(400, f"Question too long. Maximum {settings.MAX_QUESTION_LENGTH} characters.")

    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        raise HTTPException(500, "Groq API key not configured. Set GROQ_API_KEY in .env file.")

    tenant_id = current_user["tenant_id"]

    result = await process_query(
        question=question,
        user_id=current_user["user_id"],
        tenant_id=tenant_id,
        session_id=request_body.session_id,
    )

    return result


@app.post("/api/chat/stream")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat_stream(
    request_body: ChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Streaming chat endpoint — streams tokens via SSE."""
    from query.formatter import process_query_stream

    question = request_body.question.strip()

    if not question:
        raise HTTPException(400, "Question cannot be empty")

    if len(question) > settings.MAX_QUESTION_LENGTH:
        raise HTTPException(400, f"Question too long. Maximum {settings.MAX_QUESTION_LENGTH} characters.")

    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        raise HTTPException(500, "Groq API key not configured.")

    tenant_id = current_user["tenant_id"]

    async def event_generator():
        async for event in process_query_stream(
            question=question,
            user_id=current_user["user_id"],
            tenant_id=tenant_id,
            session_id=request_body.session_id,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/{query_id}/rate")
async def rate_response(
    query_id: int,
    request_body: RatingRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rate a response (thumbs up/down)."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Query).where(
            Query.id == query_id,
            Query.user_id == current_user["user_id"],
            Query.tenant_id == tenant_id,
        )
    )
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(404, "Query not found")

    query.rating = request_body.rating
    await db.flush()

    from database.audit import log_audit_action
    await log_audit_action(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        action="rate",
        resource_type="query",
        resource_id=query_id,
        details={"rating": request_body.rating},
    )

    return {"message": "Rating saved"}


@app.get("/api/chat/history")
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat sessions for the current user (within their tenant)."""
    from sqlalchemy import func

    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(
            ChatSession.id,
            ChatSession.title,
            ChatSession.created_at,
            ChatSession.updated_at,
            func.count(Query.id).label("message_count"),
        )
        .outerjoin(Query, Query.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == current_user["user_id"],
            ChatSession.tenant_id == tenant_id,
        )
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "message_count": s.message_count,
        }
        for s in sessions
    ]


@app.get("/api/chat/session/{session_id}")
async def get_session_messages(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages for a chat session."""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Query)
        .where(
            Query.session_id == session_id,
            Query.user_id == current_user["user_id"],
            Query.tenant_id == tenant_id,
        )
        .order_by(Query.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        {
            "id": m.id,
            "question": m.question,
            "answer": m.answer,
            "confidence": {
                "tier": m.confidence_tier,
                "score": m.confidence_score,
            },
            "sources": m.sources if m.sources else [],  # Already JSON, no eval!
            "is_bridge_response": m.is_bridge_response,
            "rating": m.rating,
            "response_time_ms": m.response_time_ms,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


# ── Health Check ─────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "TechAssist AI",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
    }
