"""Confidence scoring — assigns HIGH / MEDIUM / LOW tier to retrieval results."""

from config import settings


def score_confidence(raw_scores: list[float]) -> dict:
    """Calculate confidence tier from retrieval scores.

    Uses mean of top-3 scores to determine confidence level.

    Args:
        raw_scores: List of similarity scores (0-1), sorted descending.

    Returns:
        Dict with 'tier' (HIGH/MEDIUM/LOW), 'score' (float),
        and 'description' (human-readable explanation).
    """
    if not raw_scores:
        return {
            "tier": "LOW",
            "score": 0.0,
            "description": "No relevant documents found in the knowledge base.",
        }

    # Use mean of top-3 scores (or fewer if less available)
    top_scores = raw_scores[:3]
    mean_score = sum(top_scores) / len(top_scores)

    if mean_score >= settings.HIGH_CONFIDENCE_THRESHOLD:
        return {
            "tier": "HIGH",
            "score": round(mean_score, 4),
            "description": "Strong match found across multiple documents. Answer is well-supported.",
        }
    elif mean_score >= settings.MEDIUM_CONFIDENCE_THRESHOLD:
        return {
            "tier": "MEDIUM",
            "score": round(mean_score, 4),
            "description": "Partial match found. Some details may need verification with the technical team.",
        }
    else:
        return {
            "tier": "LOW",
            "score": round(mean_score, 4),
            "description": "No strong match found. A bridge response has been generated to help you respond professionally.",
        }
