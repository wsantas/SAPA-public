-- Homestead plugin: initial schema
-- Family-shared (no profile_id) session tracking

CREATE TABLE IF NOT EXISTS homestead_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type TEXT NOT NULL DEFAULT 'session',
    topic TEXT,
    prompt TEXT,
    response TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_homestead_history_topic ON homestead_history(topic);
CREATE INDEX IF NOT EXISTS idx_homestead_history_created ON homestead_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_homestead_history_type ON homestead_history(session_type);
