-- 002_similarity_procedures.sql
-- SQL functions and procedures for computing interest overlaps (synapses)

-- Function to compute top interest overlaps for a user against a provided embedding vector
-- This uses pgvector's cosine distance operator (<=>)
CREATE OR REPLACE FUNCTION compute_top_synapses(
    p_user_id INTEGER,
    p_embedding vector(1536),
    p_threshold FLOAT DEFAULT 0.70,
    p_limit INT DEFAULT 3
)
RETURNS TABLE (
    id INTEGER,
    label VARCHAR,
    similarity FLOAT,
    distance FLOAT
) AS $$
BEGIN
    -- Compute similarity (1 - distance) for each interest node
    -- pgvector's <=> operator computes cosine distance
    RETURN QUERY
    SELECT 
        interest_nodes.id,
        interest_nodes.label,
        (1 - (interest_nodes.vector <=> p_embedding))::FLOAT as similarity,
        (interest_nodes.vector <=> p_embedding)::FLOAT as distance
    FROM interest_nodes
    WHERE interest_nodes.user_id = p_user_id
    ORDER BY interest_nodes.vector <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to compute top persona matches for a user
-- This finds which personas align with a provided embedding
CREATE OR REPLACE FUNCTION compute_persona_matches(
    p_user_id INTEGER,
    p_embedding vector(1536),
    p_threshold FLOAT DEFAULT 0.70,
    p_limit INT DEFAULT 5
)
RETURNS TABLE (
    id INTEGER,
    label VARCHAR,
    weight INTEGER,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        user_persona.id,
        user_persona.label,
        user_persona.weight,
        (1 - (user_persona.vector <=> p_embedding))::FLOAT as similarity
    FROM user_persona
    WHERE user_persona.user_id = p_user_id
        AND (1 - (user_persona.vector <=> p_embedding)) >= p_threshold
    ORDER BY user_persona.vector <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to compute average similarity between two sets of vectors
-- Useful for understanding overall compatibility
CREATE OR REPLACE FUNCTION avg_vector_similarity(
    p_vector1 vector(1536),
    p_vector2 vector(1536)
)
RETURNS FLOAT AS $$
BEGIN
    RETURN (1 - (p_vector1 <=> p_vector2))::FLOAT;
END;
$$ LANGUAGE plpgsql;

-- Function to find top synapses with context (persona weight-adjusted)
-- This returns weighted matches considering both similarity and persona weight
CREATE OR REPLACE FUNCTION compute_weighted_synapses(
    p_user_id INTEGER,
    p_embedding vector(1536),
    p_threshold FLOAT DEFAULT 0.70,
    p_limit INT DEFAULT 3
)
RETURNS TABLE (
    interaction_label VARCHAR,
    persona_id INTEGER,
    persona_label VARCHAR,
    base_similarity FLOAT,
    weighted_score FLOAT
) AS $$
BEGIN
    -- This is a join that shows how interaction interests map to personas
    -- with weights applied
    RETURN QUERY
    WITH interest_similarities AS (
        SELECT
            'extracted_interest'::VARCHAR as interaction_label,
            up.id as persona_id,
            up.label as persona_label,
            (1 - (up.vector <=> p_embedding))::FLOAT as base_similarity,
            ((1 - (up.vector <=> p_embedding)) * up.weight / 10.0)::FLOAT as weighted_score
        FROM user_persona up
        WHERE up.user_id = p_user_id
            AND (1 - (up.vector <=> p_embedding)) >= p_threshold
        ORDER BY weighted_score DESC
        LIMIT p_limit
    )
    SELECT interaction_label, persona_id, persona_label, base_similarity, weighted_score 
    FROM interest_similarities;
END;
$$ LANGUAGE plpgsql;
