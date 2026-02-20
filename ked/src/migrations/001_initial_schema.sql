-- 001_initial_schema.sql
-- Initial schema for Linkd backend

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- User Personas (Anchor Data) - weighted list of interests
CREATE TABLE IF NOT EXISTS user_persona (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR NOT NULL,
    weight INTEGER DEFAULT 1,
    vector vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_persona_user ON user_persona(user_id);
CREATE INDEX IF NOT EXISTS idx_user_persona_vector ON user_persona USING ivfflat (vector vector_cosine_ops) 
    WITH (lists = 100);

-- Interest Nodes (extracted from interactions)
CREATE TABLE IF NOT EXISTS interest_nodes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR NOT NULL,
    vector vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_interest_nodes_user ON interest_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_interest_nodes_vector ON interest_nodes USING ivfflat (vector vector_cosine_ops)
    WITH (lists = 100);

-- Conversations (interaction records)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transcript TEXT,
    metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- Row Level Security Policies
ALTER TABLE user_persona ENABLE ROW LEVEL SECURITY;
ALTER TABLE interest_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policy for user_persona: users can only see their own personas
CREATE POLICY user_isolation_user_persona ON user_persona
    USING (user_id = CURRENT_SETTING('app.current_user_id')::int);

-- RLS Policy for interest_nodes: users can only see their own interests
CREATE POLICY user_isolation_interest_nodes ON interest_nodes
    USING (user_id = CURRENT_SETTING('app.current_user_id')::int);

-- RLS Policy for conversations: users can only see their own conversations
CREATE POLICY user_isolation_conversations ON conversations
    USING (user_id = CURRENT_SETTING('app.current_user_id')::int);
