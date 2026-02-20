-- 003_jobs_and_feedback.sql
-- Add job tracking, feedback, and metrics tables

-- Jobs table for async task tracking
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR DEFAULT 'pending',
    job_type VARCHAR NOT NULL,
    input_data TEXT,
    result TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    progress INTEGER DEFAULT 0
);

CREATE INDEX idx_jobs_job_id ON jobs(job_id);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- Persona feedback table
CREATE TABLE IF NOT EXISTS persona_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_id INTEGER NOT NULL REFERENCES user_persona(id) ON DELETE CASCADE,
    feedback_type VARCHAR NOT NULL,
    rating INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_persona_feedback_user_id ON persona_feedback(user_id);
CREATE INDEX idx_persona_feedback_persona_id ON persona_feedback(persona_id);
CREATE INDEX idx_persona_feedback_type ON persona_feedback(feedback_type);

-- Interaction metrics table for accuracy tracking
CREATE TABLE IF NOT EXISTS interaction_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interaction_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    mode VARCHAR NOT NULL,
    top_synapse_similarity FLOAT,
    avg_similarity FLOAT,
    extraction_accuracy FLOAT,
    processing_time_ms INTEGER,
    user_approved INTEGER DEFAULT 0,
    user_rejected INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interaction_metrics_user_id ON interaction_metrics(user_id);
CREATE INDEX idx_interaction_metrics_mode ON interaction_metrics(mode);
CREATE INDEX idx_interaction_metrics_similarity ON interaction_metrics(avg_similarity);
