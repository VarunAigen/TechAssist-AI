"""Response formatter — orchestrates the full tenant-scoped RAG pipeline.
Supports multi-turn conversation memory."""

import json
import time
import logging
from query.retriever import retrieve_chunks
from query.confidence import score_confidence
from query.generator import (
    generate_grounded_answer,
    rewrite_for_client,
    generate_bridge_response,
)
from database.session import get_db_context
from database.models import Query, ChatSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Number of previous turns to include for conversation context
CONVERSATION_MEMORY_TURNS = 5


async def _load_conversation_history(session_id: int, tenant_id: str) -> list[dict]:
    """Load recent conversation history from a session for multi-turn context.

    Args:
        session_id: Chat session ID.
        tenant_id: Tenant UUID.

    Returns:
        List of dicts with 'role' and 'content' for the LLM.
    """
    if not session_id:
        return []

    async with get_db_context() as db:
        result = await db.execute(
            select(Query)
            .where(
                Query.session_id == session_id,
                Query.tenant_id == tenant_id,
            )
            .order_by(Query.created_at.desc())
            .limit(CONVERSATION_MEMORY_TURNS)
        )
        recent_queries = result.scalars().all()

    # Reverse to chronological order
    recent_queries.reverse()

    history = []
    for q in recent_queries:
        history.append({"role": "user", "content": q.question})
        history.append({"role": "assistant", "content": q.answer})

    return history


async def process_query(
    question: str,
    user_id: int,
    tenant_id: str,
    session_id: int = None,
) -> dict:
    """Full RAG pipeline: Retrieve → Score → Generate → Format.

    Includes multi-turn conversation memory from the current session.

    Args:
        question: The BD rep's question.
        user_id: Current user's ID.
        tenant_id: Tenant UUID for knowledge base scoping.
        session_id: Optional chat session ID.

    Returns:
        Dict with answer, confidence, sources, bridge_response, etc.
    """
    start_time = time.time()

    # Step 0: Load conversation history for multi-turn context
    conversation_history = await _load_conversation_history(session_id, tenant_id)

    # Step 1: Retrieve relevant chunks from tenant's knowledge base
    retrieval = retrieve_chunks(question, tenant_id=tenant_id)
    chunks = retrieval["chunks"]
    raw_scores = retrieval["raw_scores"]

    # Step 2: Score confidence
    confidence = score_confidence(raw_scores)
    tier = confidence["tier"]

    # Step 3: Generate response based on tier
    sources = []
    bridge_script = None
    is_bridge = False

    try:
        if tier == "HIGH":
            raw_answer = generate_grounded_answer(question, chunks, conversation_history)
            final_answer = rewrite_for_client(raw_answer)
            sources = _format_sources(chunks[:3])

        elif tier == "MEDIUM":
            raw_answer = generate_grounded_answer(question, chunks, conversation_history)
            final_answer = rewrite_for_client(raw_answer)
            sources = _format_sources(chunks[:3])
            bridge_script = generate_bridge_response(question, chunks)

        else:
            is_bridge = True
            bridge_script = generate_bridge_response(question, chunks)
            final_answer = bridge_script
            sources = _format_sources(chunks[:2]) if chunks else []

    except Exception as e:
        logger.error(f"LLM generation failed: {e}", extra={"tenant_id": tenant_id, "user_id": user_id})
        final_answer = (
            "I'm having trouble processing your question right now. "
            "Please try again in a moment, or contact your admin if this persists."
        )
        confidence = {"tier": "LOW", "score": 0.0, "description": "Generation error"}
        is_bridge = True

    response_time_ms = (time.time() - start_time) * 1000

    # Step 4: Log query to database
    query_id, actual_session_id = await _log_query(
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        question=question,
        answer=final_answer,
        confidence=confidence,
        sources=sources,
        is_bridge=is_bridge,
        response_time_ms=response_time_ms,
    )

    logger.info(
        f"Query processed: tier={tier}, score={confidence['score']:.3f}, time={response_time_ms:.0f}ms, history_turns={len(conversation_history) // 2}",
        extra={"tenant_id": tenant_id, "user_id": user_id},
    )

    return {
        "id": query_id,
        "session_id": actual_session_id,
        "question": question,
        "answer": final_answer,
        "confidence": confidence,
        "sources": sources,
        "bridge_response": bridge_script,
        "is_bridge_response": is_bridge,
        "response_time_ms": round(response_time_ms),
    }


async def process_query_stream(
    question: str,
    user_id: int,
    tenant_id: str,
    session_id: int = None,
):
    """Streaming RAG pipeline: Retrieve → Score → Stream Generate.

    Yields SSE events as tokens arrive, then a final metadata event.

    Yields:
        str: SSE-formatted event strings.
    """
    from query.generator import generate_grounded_answer_stream

    start_time = time.time()

    # Load conversation history
    conversation_history = await _load_conversation_history(session_id, tenant_id)

    # Retrieve
    retrieval = retrieve_chunks(question, tenant_id=tenant_id)
    chunks = retrieval["chunks"]
    raw_scores = retrieval["raw_scores"]

    # Score confidence
    confidence = score_confidence(raw_scores)
    tier = confidence["tier"]

    sources = _format_sources(chunks[:3]) if chunks else []
    bridge_script = None
    is_bridge = False
    full_answer = ""

    try:
        if tier in ("HIGH", "MEDIUM"):
            # Stream the grounded answer
            for token in generate_grounded_answer_stream(question, chunks, conversation_history):
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # For MEDIUM, also generate bridge script (non-streaming)
            if tier == "MEDIUM":
                bridge_script = generate_bridge_response(question, chunks)

        else:
            # LOW — bridge response (non-streaming since it's short)
            is_bridge = True
            bridge_script = generate_bridge_response(question, chunks)
            full_answer = bridge_script
            yield f"data: {json.dumps({'type': 'token', 'content': full_answer})}\n\n"

    except Exception as e:
        logger.error(f"Stream generation failed: {e}", extra={"tenant_id": tenant_id})
        full_answer = "I'm having trouble processing your question right now. Please try again."
        confidence = {"tier": "LOW", "score": 0.0, "description": "Generation error"}
        is_bridge = True
        yield f"data: {json.dumps({'type': 'token', 'content': full_answer})}\n\n"

    response_time_ms = (time.time() - start_time) * 1000

    # Log to database
    query_id, actual_session_id = await _log_query(
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        question=question,
        answer=full_answer,
        confidence=confidence,
        sources=sources,
        is_bridge=is_bridge,
        response_time_ms=response_time_ms,
    )

    # Send final metadata event
    metadata = {
        "type": "done",
        "id": query_id,
        "session_id": actual_session_id,
        "confidence": confidence,
        "sources": sources,
        "bridge_response": bridge_script,
        "is_bridge_response": is_bridge,
        "response_time_ms": round(response_time_ms),
    }
    yield f"data: {json.dumps(metadata)}\n\n"

    logger.info(
        f"Streamed query: tier={tier}, time={response_time_ms:.0f}ms",
        extra={"tenant_id": tenant_id, "user_id": user_id},
    )


def _format_sources(chunks: list[dict]) -> list[dict]:
    """Format source chunks for the frontend."""
    sources = []
    seen_files = set()
    for chunk in chunks:
        filename = chunk["metadata"].get("filename", "Unknown")
        if filename not in seen_files:
            sources.append({
                "filename": filename,
                "preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "score": chunk["score"],
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
            })
            seen_files.add(filename)
    return sources


async def _log_query(
    user_id: int,
    tenant_id: str,
    session_id: int,
    question: str,
    answer: str,
    confidence: dict,
    sources: list,
    is_bridge: bool,
    response_time_ms: float,
) -> tuple[int, int]:
    """Log the query and response to the database."""
    async with get_db_context() as db:
        if not session_id:
            session = ChatSession(
                tenant_id=tenant_id,
                user_id=user_id,
                title=question[:50] + "..." if len(question) > 50 else question,
            )
            db.add(session)
            await db.flush()
            session_id = session.id

        query = Query(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            question=question,
            answer=answer,
            confidence_tier=confidence["tier"],
            confidence_score=confidence["score"],
            sources=sources,
            is_bridge_response=is_bridge,
            response_time_ms=response_time_ms,
        )
        db.add(query)
        await db.flush()
        query_id = query.id

    return query_id, session_id
