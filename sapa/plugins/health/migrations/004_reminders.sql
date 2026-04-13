CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    protocol_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    schedule TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reminders_profile ON reminders(profile_id);
CREATE INDEX IF NOT EXISTS idx_reminders_enabled ON reminders(enabled);
