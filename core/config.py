from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def env_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


def env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    api_id: int = field(default_factory=lambda: env_int("API_ID"))
    api_hash: str = field(default_factory=lambda: os.getenv("API_HASH", "").strip())
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", "").strip())
    session_string: str = field(default_factory=lambda: os.getenv("SESSION_STRING", "").strip())
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    openweather_api_key: str = field(default_factory=lambda: os.getenv("OPENWEATHER_API_KEY", "").strip())
    logger_id: int = field(default_factory=lambda: env_int("LOGGER_ID", -1003009782265))
    default_voice: str = field(default_factory=lambda: os.getenv("RUHI_DEFAULT_VOICE", "hi-IN-SwaraNeural"))
    database_path: Path = field(default_factory=lambda: Path(os.getenv("DATABASE_PATH", "ruhi_supreme.db")))
    temp_dir: Path = field(default_factory=lambda: Path(os.getenv("RUHI_TEMP_DIR", "tmp")))
    max_queue: int = field(default_factory=lambda: env_int("MAX_QUEUE_LIMIT", 50))
    max_playlist: int = field(default_factory=lambda: env_int("MAX_PLAYLIST_SIZE", 25))
    voice_concurrency: int = field(default_factory=lambda: env_int("VOICE_CONCURRENCY", 2))
    wake_words: list[str] = field(default_factory=lambda: env_list("WAKE_WORDS", "ruhi,roohi"))
    empty_audio: str = field(default_factory=lambda: os.getenv("EMPTY_AUDIO", "https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"))

    def validate(self) -> None:
        missing = []
        if not self.api_id:
            missing.append("API_ID")
        for name, value in {
            "API_HASH": self.api_hash,
            "BOT_TOKEN": self.bot_token,
            "SESSION_STRING": self.session_string,
        }.items():
            if not value:
                missing.append(name)
        if missing:
            raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
