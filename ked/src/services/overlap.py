import logging
from sqlalchemy import text
from ..db import engine

logger = logging.getLogger(__name__)


def compute_top_synapses(
    user_id: int,
    embedding_vector,
    threshold: float = 0.7,
    top_k: int = 3,
) -> list[dict]:
    """Compute top interest overlaps (synapses) for a user.

    Uses the PostgreSQL function compute_top_synapses() via pgvector.
    Calls the stored procedure to find the top_k interest nodes with similarity >= threshold.

    Args:
        user_id: User ID
        embedding_vector: Vector embedding (1536 dims, from Gemini) to match against
        threshold: Minimum similarity score (0-1). Default 0.70
        top_k: Maximum number of results to return. Default 3

    Returns:
        List of dicts with keys: id, label, similarity
    """
    query = text(
        "SELECT id, label, similarity, distance "
        "FROM compute_top_synapses(:uid, :vec::vector, :threshold, :k);"
    )
    try:
        with engine.connect() as conn:
            result = conn.execute(
                query,
                {"uid": user_id, "vec": embedding_vector, "threshold": threshold, "k": top_k},
            ).fetchall()

        synapses = []
        for row in result:
            if row.similarity >= threshold:
                synapses.append(
                    {
                        "id": row.id,
                        "label": row.label,
                        "similarity": float(row.similarity),
                        "distance": float(row.distance),
                    }
                )
        logger.info(f"[user_id={user_id}] Found {len(synapses)} synapses")
        return synapses
    except Exception as e:
        logger.error(f"Error computing synapses for user {user_id}: {e}")
        return []


def compute_persona_matches(
    user_id: int,
    embedding_vector,
    threshold: float = 0.7,
    top_k: int = 5,
) -> list[dict]:
    """Compute persona matches for a user.

    Uses the PostgreSQL function compute_persona_matches() to find personas
    that match a given embedding with a similarity score >= threshold.

    Args:
        user_id: User ID
        embedding_vector: Vector embedding (1536 dims, from Gemini) to match against
        threshold: Minimum similarity score (0-1). Default 0.70
        top_k: Maximum number of results. Default 5

    Returns:
        List of dicts with keys: id, label, weight, similarity
    """
    query = text(
        "SELECT id, label, weight, similarity "
        "FROM compute_persona_matches(:uid, :vec::vector, :threshold, :k);"
    )
    try:
        with engine.connect() as conn:
            result = conn.execute(
                query,
                {"uid": user_id, "vec": embedding_vector, "threshold": threshold, "k": top_k},
            ).fetchall()

        matches = []
        for row in result:
            matches.append(
                {
                    "persona_id": row.id,
                    "label": row.label,
                    "weight": row.weight,
                    "similarity": float(row.similarity),
                }
            )
        logger.info(f"[user_id={user_id}] Found {len(matches)} persona matches")
        return matches
    except Exception as e:
        logger.error(f"Error computing persona matches for user {user_id}: {e}")
        return []


def compute_weighted_synapses(
    user_id: int,
    embedding_vector,
    threshold: float = 0.7,
    top_k: int = 3,
) -> list[dict]:
    """Compute weighted synapses (considers persona weight).

    Uses the PostgreSQL function compute_weighted_synapses() to compute
    interest overlaps with persona weights factored in.

    Args:
        user_id: User ID
        embedding_vector: Vector embedding (1536 dims, from Gemini)
        threshold: Minimum similarity. Default 0.70
        top_k: Max results. Default 3

    Returns:
        List of dicts with keys: interaction_label, persona_id, persona_label, base_similarity, weighted_score
    """
    query = text(
        "SELECT interaction_label, persona_id, persona_label, base_similarity, weighted_score "
        "FROM compute_weighted_synapses(:uid, :vec::vector, :threshold, :k);"
    )
    try:
        with engine.connect() as conn:
            result = conn.execute(
                query,
                {"uid": user_id, "vec": embedding_vector, "threshold": threshold, "k": top_k},
            ).fetchall()

        synapses = []
        for row in result:
            synapses.append(
                {
                    "interaction_label": row.interaction_label,
                    "persona_id": row.persona_id,
                    "persona_label": row.persona_label,
                    "base_similarity": float(row.base_similarity),
                    "weighted_score": float(row.weighted_score),
                }
            )
        logger.info(f"[user_id={user_id}] Found {len(synapses)} weighted synapses")
        return synapses
    except Exception as e:
        logger.error(f"Error computing weighted synapses for user {user_id}: {e}")
        return []
