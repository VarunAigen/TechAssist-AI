"""Retriever — tenant-scoped semantic search over ChromaDB vectors."""

import logging
from ingestion.embedder import get_collection, generate_embeddings
from config import settings

logger = logging.getLogger(__name__)


def retrieve_chunks(query: str, tenant_id: str = None, top_k: int = None) -> dict:
    """Perform semantic search within a tenant's knowledge base.

    Args:
        query: The user's question.
        tenant_id: Tenant UUID — searches only this tenant's collection.
        top_k: Number of results to return.

    Returns:
        Dict with 'chunks' (list of dicts with text, score, metadata)
        and 'raw_scores' (list of float distances).
    """
    top_k = top_k or settings.TOP_K_RESULTS
    collection = get_collection(tenant_id)

    # Check if collection has any documents
    if collection.count() == 0:
        logger.info("No documents in collection", extra={"tenant_id": tenant_id})
        return {"chunks": [], "raw_scores": []}

    # Generate query embedding
    query_embedding = generate_embeddings([query])[0]

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    raw_scores = []

    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 - (distance / 2)
            distance = results["distances"][0][i]
            similarity = 1 - (distance / 2)

            chunks.append({
                "text": doc,
                "score": round(similarity, 4),
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            })
            raw_scores.append(similarity)

    # Sort by score descending
    chunks.sort(key=lambda x: x["score"], reverse=True)
    raw_scores.sort(reverse=True)

    logger.info(
        f"Retrieved {len(chunks)} chunks for query (top score: {raw_scores[0]:.3f})" if raw_scores else "No chunks found",
        extra={"tenant_id": tenant_id},
    )

    return {"chunks": chunks, "raw_scores": raw_scores}
