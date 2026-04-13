CREATE TABLE IF NOT EXISTS protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    started_at TEXT NOT NULL,
    phases TEXT,
    current_phase INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_protocols_profile ON protocols(profile_id);
CREATE INDEX IF NOT EXISTS idx_protocols_status ON protocols(status);
