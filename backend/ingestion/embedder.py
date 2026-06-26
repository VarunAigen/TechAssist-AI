"""Embedding engine — supports Ollama (nomic-embed-text) and sentence-transformers fallback.
Also handles tenant-scoped ChromaDB storage.

Performance optimizations:
- Ollama: concurrent HTTP requests in batches
- Sentence-transformers: batch encoding
- ChromaDB: batch upserts to avoid memory spikes
"""

import logging
import chromadb
import httpx
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import settings

logger = logging.getLogger(__name__)

# Tuning constants
OLLAMA_BATCH_CONCURRENCY = 10   # Max parallel Ollama HTTP requests
ST_BATCH_SIZE = 64              # Sentence-transformers encode batch size
CHROMA_UPSERT_BATCH = 100       # Max chunks per ChromaDB upsert call

# Global references
_chroma_client = None
_collections = {}  # Cache: tenant_id → collection
_st_model = None


def get_chroma_client():
    """Get or create ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        logger.info(f"ChromaDB client initialized at {settings.CHROMA_PERSIST_DIR}")
    return _chroma_client


def get_collection(tenant_id: str = None):
    """Get or create the knowledge base collection for a specific tenant.
    
    Args:
        tenant_id: The tenant's UUID. If None, uses a default collection (for migration).
    
    Returns:
        ChromaDB collection scoped to the tenant.
    """
    global _collections

    if tenant_id is None:
        collection_name = "knowledge_base"  # Legacy default
    else:
        collection_name = f"{settings.CHROMA_COLLECTION_PREFIX}{tenant_id}"

    if collection_name not in _collections:
        client = get_chroma_client()
        _collections[collection_name] = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection ready: {collection_name}")

    return _collections[collection_name]


def _get_st_model():
    """Lazy-load sentence-transformers model."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(settings.ST_MODEL_NAME)
        logger.info(f"Loaded sentence-transformers model: {settings.ST_MODEL_NAME}")
    return _st_model


def _embed_single_ollama(text: str) -> list[float]:
    """Embed a single text with Ollama (used as a worker in thread pool)."""
    response = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/embeddings",
        json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def _embed_with_ollama(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using Ollama with concurrent requests.

    Uses a thread pool to send up to OLLAMA_BATCH_CONCURRENCY parallel
    HTTP requests, dramatically faster for large documents.
    """
    embeddings = [None] * len(texts)

    with ThreadPoolExecutor(max_workers=OLLAMA_BATCH_CONCURRENCY) as executor:
        future_to_idx = {
            executor.submit(_embed_single_ollama, text): idx
            for idx, text in enumerate(texts)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            embeddings[idx] = future.result()  # Preserves original order

    return embeddings


def _embed_with_st(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using sentence-transformers with batch encoding.

    Processes texts in batches of ST_BATCH_SIZE to balance speed and memory.
    """
    model = _get_st_model()
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        batch_size=ST_BATCH_SIZE,
    )
    return embeddings.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using configured provider.

    Tries Ollama first if configured, falls back to sentence-transformers.
    For large batches, logs progress.
    """
    count = len(texts)
    if count > 50:
        logger.info(f"Generating embeddings for {count} chunks (this may take a moment)...")

    if settings.EMBEDDING_PROVIDER == "ollama":
        try:
            return _embed_with_ollama(texts)
        except Exception as e:
            logger.warning(f"Ollama embedding failed ({e}), falling back to sentence-transformers")
            return _embed_with_st(texts)
    else:
        return _embed_with_st(texts)


def store_chunks(
    chunks: list[str],
    doc_id: int,
    filename: str,
    file_type: str,
    tenant_id: str = None,
) -> int:
    """Embed and store document chunks in the tenant's ChromaDB collection.

    Processes in batches of CHROMA_UPSERT_BATCH to keep memory usage
    bounded and avoid timeouts with very large documents.

    Args:
        chunks: List of text chunks.
        doc_id: Database document ID.
        filename: Original filename.
        file_type: File extension (pdf, md, etc.).
        tenant_id: Tenant UUID for collection scoping.

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_collection(tenant_id)
    total_stored = 0
    total_chunks = len(chunks)

    # Process in batches for memory efficiency
    for batch_start in range(0, total_chunks, CHROMA_UPSERT_BATCH):
        batch_end = min(batch_start + CHROMA_UPSERT_BATCH, total_chunks)
        batch = chunks[batch_start:batch_end]

        # Generate unique IDs for this batch
        ids = [
            f"doc{doc_id}_chunk{i}_{hashlib.md5(chunk[:50].encode()).hexdigest()[:8]}"
            for i, chunk in enumerate(batch, start=batch_start)
        ]

        # Metadata for this batch
        metadatas = [
            {
                "doc_id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "chunk_index": i,
                "total_chunks": total_chunks,
                "tenant_id": tenant_id or "default",
            }
            for i in range(batch_start, batch_end)
        ]

        # Generate embeddings for this batch
        embeddings = generate_embeddings(batch)

        # Upsert into ChromaDB (upsert avoids duplicate errors on retry)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=batch,
            metadatas=metadatas,
        )

        total_stored += len(batch)
        if total_chunks > CHROMA_UPSERT_BATCH:
            logger.info(
                f"Stored batch {batch_start}-{batch_end} of {total_chunks} chunks for '{filename}'",
                extra={"tenant_id": tenant_id},
            )

    logger.info(
        f"Stored {total_stored} chunks for '{filename}' in tenant collection",
        extra={"tenant_id": tenant_id},
    )
    return total_stored


def delete_document_chunks(doc_id: int, tenant_id: str = None):
    """Delete all chunks for a document from the tenant's ChromaDB collection."""
    collection = get_collection(tenant_id)
    results = collection.get(where={"doc_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])
        logger.info(
            f"Deleted {len(results['ids'])} chunks for doc_id={doc_id}",
            extra={"tenant_id": tenant_id},
        )


def get_collection_stats(tenant_id: str = None) -> dict:
    """Get stats about a tenant's ChromaDB collection."""
    collection = get_collection(tenant_id)
    count = collection.count()
    return {
        "total_chunks": count,
        "collection_name": collection.name,
    }
