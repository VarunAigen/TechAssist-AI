"""LLM Generator — generates answers using Groq API with strict grounding.

Supports conversation history for multi-turn context and streaming responses.
"""

import logging
import time
from groq import Groq
from config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazy-init Groq client."""
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


# ── System Prompts ──────────────────────────────────────────

GROUNDED_SYSTEM_PROMPT = """You are a technical knowledge assistant for a business development team. Your role is to answer client questions using ONLY the provided context documents.

CRITICAL RULES:
1. Answer ONLY using information from the provided context. Do NOT use any external knowledge.
2. If the context contains relevant information, provide a clear, accurate answer.
3. If the context only partially answers the question, state what IS confirmed from the documents and clearly indicate what information is missing.
4. If the context does not contain relevant information, say so clearly.
5. Always be factual — never guess or speculate.
6. Keep answers concise — aim for 2-4 sentences for simple questions, up to a short paragraph for complex ones.
7. Reference which document(s) the information comes from when possible.
8. If there is conversation history, use it to understand follow-up questions (e.g., "Tell me more about that" or "What about the pricing?"). Still only answer from context documents.
9. Format your response with markdown when appropriate — use **bold** for emphasis, bullet points for lists, and `code` for technical terms."""

TONE_SYSTEM_PROMPT = """You are a communication specialist. Rewrite the following technical answer in plain, client-friendly language.

RULES:
1. Remove all technical jargon — explain concepts simply.
2. Keep the answer concise — maximum 3-4 sentences.
3. Maintain accuracy — do not add information that wasn't in the original answer.
4. Use a warm, professional tone suitable for a business meeting.
5. If the answer mentions uncertainty, frame it positively (e.g., "I'd like to get you the precise details" instead of "I don't know").
6. Do NOT add greetings or sign-offs.
7. Preserve any markdown formatting (bold, lists, etc.)."""

BRIDGE_SYSTEM_PROMPT = """You are a communication coach for business development professionals. A client has asked a question that our knowledge base cannot fully answer.

Your task: Generate a professional "bridge response" that the BD rep can use immediately in a client meeting.

The bridge response MUST:
1. Start by acknowledging what IS known (use the adjacent context provided).
2. Gracefully indicate that specific details need verification.
3. Commit to a follow-up timeline (e.g., "by end of day" or "by tomorrow").
4. Sound confident and professional — NOT like "I don't know."

EXAMPLE FORMAT:
"What I can confirm is that [known fact from docs]. For the specific detail you're asking about, I want to make sure I give you the most accurate answer — let me verify with our technical team and get back to you by [timeline]."

Keep it to 2-3 sentences maximum."""


def _call_llm(messages: list[dict], temperature: float = 0.1, max_tokens: int = 500, retries: int = 2) -> str:
    """Call the Groq LLM with retry logic."""
    client = _get_client()
    last_error = None

    for attempt in range(retries + 1):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30.0,
            )
            duration = (time.time() - start) * 1000
            logger.info(f"LLM call completed in {duration:.0f}ms (attempt {attempt + 1})")
            return response.choices[0].message.content

        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 2 ** attempt
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{retries + 1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"LLM call failed after {retries + 1} attempts: {e}")

    raise last_error


def _build_context_message(question: str, context_chunks: list[dict], conversation_history: list[dict] = None) -> list[dict]:
    """Build the messages list with context, conversation history, and current question."""
    # Format context
    context_text = "\n\n---\n\n".join([
        f"[Source: {chunk['metadata'].get('filename', 'unknown')}]\n{chunk['text']}"
        for chunk in context_chunks
    ])

    messages = [{"role": "system", "content": GROUNDED_SYSTEM_PROMPT}]

    # Add conversation history if available
    if conversation_history:
        # Add a note about the conversation context
        messages.append({
            "role": "system",
            "content": f"The user has been having a conversation. Here are the previous {len(conversation_history) // 2} exchanges. Use them to understand follow-up questions.",
        })
        messages.extend(conversation_history)

    # Add current question with context
    messages.append({
        "role": "user",
        "content": f"CONTEXT DOCUMENTS:\n{context_text}\n\n---\n\nQUESTION: {question}",
    })

    return messages


def generate_grounded_answer(question: str, context_chunks: list[dict], conversation_history: list[dict] = None) -> str:
    """Generate an answer strictly grounded in the provided context.

    Args:
        question: The user's question.
        context_chunks: List of dicts with 'text' and 'metadata'.
        conversation_history: Optional list of previous messages for multi-turn context.

    Returns:
        The generated answer string.
    """
    messages = _build_context_message(question, context_chunks, conversation_history)
    return _call_llm(messages, temperature=0.1, max_tokens=500)


def generate_grounded_answer_stream(question: str, context_chunks: list[dict], conversation_history: list[dict] = None):
    """Stream a grounded answer token by token.

    Args:
        question: The user's question.
        context_chunks: List of dicts with 'text' and 'metadata'.
        conversation_history: Optional list of previous messages.

    Yields:
        str: Individual tokens as they arrive from the LLM.
    """
    client = _get_client()
    messages = _build_context_message(question, context_chunks, conversation_history)

    try:
        start = time.time()
        stream = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
            stream=True,
            timeout=30.0,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        duration = (time.time() - start) * 1000
        logger.info(f"LLM stream completed in {duration:.0f}ms")

    except Exception as e:
        logger.error(f"LLM stream failed: {e}")
        yield f"\n\n*Error: Could not complete the response. Please try again.*"


def rewrite_for_client(technical_answer: str) -> str:
    """Rewrite a technical answer in plain, client-friendly language."""
    return _call_llm(
        messages=[
            {"role": "system", "content": TONE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Rewrite this for a client meeting:\n\n{technical_answer}"},
        ],
        temperature=0.3,
        max_tokens=300,
    )


def generate_bridge_response(question: str, adjacent_chunks: list[dict]) -> str:
    """Generate a bridge response for low-confidence situations."""
    adjacent_context = "\n".join([
        f"- {chunk['text'][:200]}..." for chunk in adjacent_chunks[:3]
    ]) if adjacent_chunks else "No related information available."

    return _call_llm(
        messages=[
            {"role": "system", "content": BRIDGE_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"CLIENT QUESTION: {question}\n\n"
                f"AVAILABLE ADJACENT KNOWLEDGE:\n{adjacent_context}\n\n"
                f"Generate a bridge response the BD rep can use right now."
            )},
        ],
        temperature=0.4,
        max_tokens=250,
    )
