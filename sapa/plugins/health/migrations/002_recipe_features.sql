-- Recipe favorites, cook log, and grocery source column

CREATE TABLE IF NOT EXISTS recipe_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    recipe_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    UNIQUE(profile_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS recipe_cook_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    recipe_id TEXT NOT NULL,
    servings REAL DEFAULT 1,
    cooked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

-- Add source column to grocery_list (manual or generated)
ALTER TABLE grocery_list ADD COLUMN source TEXT DEFAULT 'manual';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_recipe_favorites_profile ON recipe_favorites(profile_id);
CREATE INDEX IF NOT EXISTS idx_recipe_cook_log_profile ON recipe_cook_log(profile_id);
CREATE INDEX IF NOT EXISTS idx_recipe_cook_log_recipe ON recipe_cook_log(recipe_id);
