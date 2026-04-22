-- Hermes plugin: chat history
-- Family-shared (no profile_id) — local AI assistant for the family

CREATE TABLE IF NOT EXISTS hermes_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    model TEXT,
    backend TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hermes_chat_created ON hermes_chat(created_at DESC);
