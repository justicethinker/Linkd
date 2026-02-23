-- initial schema for Linkd backend
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Create Tables with safety checks
CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY,
    email text UNIQUE NOT NULL,
    hashed_password text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_persona (
    id serial PRIMARY KEY,
    user_id int NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label text NOT NULL,
    weight int DEFAULT 1,
    vector vector(1536)
);

CREATE TABLE IF NOT EXISTS interest_nodes (
    id serial PRIMARY KEY,
    user_id int NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label text NOT NULL,
    vector vector(1536),
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id serial PRIMARY KEY,
    user_id int NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transcript text,
    metadata text,
    created_at timestamptz DEFAULT now()
);

-- 2. Enable Row Level Security
ALTER TABLE user_persona ENABLE ROW LEVEL SECURITY;
ALTER TABLE interest_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- 3. Drop and Re-create Policies (Postgres workaround for IF NOT EXISTS)
DROP POLICY IF EXISTS user_isolation_user_persona ON user_persona;
CREATE POLICY user_isolation_user_persona ON user_persona
    USING (user_id = current_setting('app.current_user_id')::int);

DROP POLICY IF EXISTS user_isolation_interest_nodes ON interest_nodes;
CREATE POLICY user_isolation_interest_nodes ON interest_nodes
    USING (user_id = current_setting('app.current_user_id')::int);

DROP POLICY IF EXISTS user_isolation_conversations ON conversations;
CREATE POLICY user_isolation_conversations ON conversations
    USING (user_id = current_setting('app.current_user_id')::int);
