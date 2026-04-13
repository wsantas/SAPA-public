-- Homestead plugin: add topics table for gap analysis
-- Family-shared (no profile_id)

CREATE TABLE IF NOT EXISTS homestead_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    first_learned TIMESTAMP NOT NULL,
    last_reviewed TIMESTAMP NOT NULL,
    review_count INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_homestead_topics_name ON homestead_topics(name);
