"""Gap analysis targets — customize per profile."""

JOHN_GAP_TARGETS = {
    "Strength Training": {
        "priority": "critical",
        "topics": [
            "progressive overload", "compound movements", "squat", "deadlift",
            "bench press", "overhead press", "barbell", "periodization",
        ],
    },
    "Recovery": {
        "priority": "high",
        "topics": [
            "sleep", "rest days", "deload", "foam rolling", "stretching",
            "mobility", "cold therapy", "contrast therapy",
        ],
    },
    "Nutrition": {
        "priority": "high",
        "topics": [
            "protein", "macros", "meal prep", "caloric surplus", "caloric deficit",
            "hydration", "electrolytes", "supplements",
        ],
    },
}

JANE_GAP_TARGETS = {
    "Mobility & Flexibility": {
        "priority": "critical",
        "topics": [
            "hip mobility", "ankle mobility", "thoracic spine", "stretching",
            "yoga", "foam rolling", "dynamic warmup",
        ],
    },
    "Running": {
        "priority": "high",
        "topics": [
            "5k", "10k", "tempo run", "intervals", "cadence",
            "running form", "easy run", "long run",
        ],
    },
    "Recovery": {
        "priority": "high",
        "topics": [
            "sleep", "rest days", "nutrition", "hydration",
            "electrolytes", "massage", "contrast therapy",
        ],
    },
}

PROFILE_GAP_TARGETS = {
    1: JOHN_GAP_TARGETS,
    2: JANE_GAP_TARGETS,
}
