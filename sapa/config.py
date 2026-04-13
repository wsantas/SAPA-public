"""Configuration management for SAPA."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Configuration settings for SAPA."""

    # API Keys
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))

    # User preferences
    user_name: str = "User"

    # Paths — override with SAPA_CONFIG_DIR env var, defaults to ~/.sapa-public
    config_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("SAPA_CONFIG_DIR", str(Path.home() / ".sapa-public"))
        )
    )
    config_file: Path = field(init=False)
    logs_dir: Path = field(init=False)
    daily_dir: Path = field(init=False)

    def __post_init__(self):
        self.config_file = self.config_dir / "config.json"
        self.logs_dir = self.config_dir / "logs"
        self.daily_dir = self.config_dir / "daily"

    def ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        self.ensure_directories()
        config_data = {
            "user_name": self.user_name,
        }
        with open(self.config_file, "w") as f:
            json.dump(config_data, f, indent=2)

    def load(self) -> bool:
        if not self.config_file.exists():
            return False
        try:
            with open(self.config_file) as f:
                config_data = json.load(f)
            self.user_name = config_data.get("user_name", self.user_name)
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    @property
    def db_path(self) -> Path:
        return self.config_dir / "learning.db"

    @property
    def inbox_path(self) -> Path:
        return self.config_dir / "plugins" / "health" / "inbox"

    @property
    def homestead_inbox_path(self) -> Path:
        return self.config_dir / "plugins" / "homestead" / "inbox"


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
        _config.load()
    return _config


def reset_config() -> None:
    global _config
    _config = None
