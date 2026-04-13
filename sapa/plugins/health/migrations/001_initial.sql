-- Health Bot plugin initial schema
-- All tables use IF NOT EXISTS for safe re-runs

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    first_learned TIMESTAMP NOT NULL,
    last_reviewed TIMESTAMP NOT NULL,
    review_count INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.5,
    next_review TIMESTAMP,
    profile_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    UNIQUE(name, profile_id)
);

CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    score REAL NOT NULL,
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS streaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1,
    current INTEGER DEFAULT 0,
    longest INTEGER DEFAULT 0,
    last_active DATE,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    UNIQUE(profile_id)
);

CREATE TABLE IF NOT EXISTS daily_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date DATE NOT NULL,
    topics_learned INTEGER DEFAULT 0,
    quizzes_taken INTEGER DEFAULT 0,
    profile_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    UNIQUE(session_date, profile_id)
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type TEXT NOT NULL,
    topic TEXT,
    prompt TEXT,
    response TEXT,
    notes TEXT,
    profile_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    profile_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

-- HULK Protocol Tables

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    duration INTEGER,
    total_sets INTEGER,
    total_reps INTEGER,
    rpe INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    sets INTEGER,
    reps TEXT,
    weight TEXT,
    rpe INTEGER,
    notes TEXT,
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recovery_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    sleep_hours REAL,
    sleep_quality INTEGER,
    soreness INTEGER,
    energy INTEGER,
    stress INTEGER,
    motivation INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    UNIQUE(date, profile_id)
);

CREATE TABLE IF NOT EXISTS body_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    weight REAL,
    waist REAL,
    chest REAL,
    arms REAL,
    body_fat REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS meal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    meal_name TEXT NOT NULL,
    category TEXT,
    calories INTEGER,
    protein INTEGER,
    carbs INTEGER,
    fat INTEGER,
    date TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    target REAL NOT NULL,
    current REAL,
    unit TEXT NOT NULL,
    deadline TEXT,
    completed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS personal_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    exercise TEXT NOT NULL,
    weight REAL NOT NULL,
    reps INTEGER NOT NULL,
    estimated_1rm REAL,
    workout_id INTEGER,
    date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE SET NULL
);

-- Meal Planner Tables

CREATE TABLE IF NOT EXISTS meal_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    recipe_id TEXT,
    recipe_name TEXT NOT NULL,
    notes TEXT,
    requested_date TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_date TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    recipe_id TEXT,
    recipe_name TEXT NOT NULL,
    notes TEXT,
    request_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES meal_requests(id)
);

CREATE TABLE IF NOT EXISTS grocery_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    category TEXT DEFAULT 'other',
    quantity TEXT,
    checked INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes

CREATE INDEX IF NOT EXISTS idx_topics_name ON topics(name);
CREATE INDEX IF NOT EXISTS idx_topics_profile ON topics(profile_id);
CREATE INDEX IF NOT EXISTS idx_topics_next_review ON topics(next_review);
CREATE INDEX IF NOT EXISTS idx_quiz_results_topic ON quiz_results(topic_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at);
CREATE INDEX IF NOT EXISTS idx_history_profile ON history(profile_id);
CREATE INDEX IF NOT EXISTS idx_notes_topic ON notes(topic);
CREATE INDEX IF NOT EXISTS idx_notes_profile ON notes(profile_id);
CREATE INDEX IF NOT EXISTS idx_daily_sessions_profile ON daily_sessions(profile_id);
CREATE INDEX IF NOT EXISTS idx_workouts_profile ON workouts(profile_id);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
CREATE INDEX IF NOT EXISTS idx_exercises_workout ON exercises(workout_id);
CREATE INDEX IF NOT EXISTS idx_recovery_profile ON recovery_logs(profile_id);
CREATE INDEX IF NOT EXISTS idx_recovery_date ON recovery_logs(date);
CREATE INDEX IF NOT EXISTS idx_body_logs_profile ON body_logs(profile_id);
CREATE INDEX IF NOT EXISTS idx_meal_logs_profile ON meal_logs(profile_id);
CREATE INDEX IF NOT EXISTS idx_meal_logs_date ON meal_logs(date);
CREATE INDEX IF NOT EXISTS idx_goals_profile ON goals(profile_id);
CREATE INDEX IF NOT EXISTS idx_prs_profile ON personal_records(profile_id);
CREATE INDEX IF NOT EXISTS idx_prs_exercise ON personal_records(exercise);
CREATE INDEX IF NOT EXISTS idx_meal_requests_profile ON meal_requests(profile_id);
CREATE INDEX IF NOT EXISTS idx_meal_requests_status ON meal_requests(status);
CREATE INDEX IF NOT EXISTS idx_meal_plans_date ON meal_plans(plan_date);
