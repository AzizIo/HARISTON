import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    database_path: str


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and set the token.")
    raw_admins = os.getenv("ADMIN_IDS", "")
    admin_values = [value.strip() for value in raw_admins.split(",") if value.strip()]
    invalid_admins = [value for value in admin_values if not value.isdigit()]
    if invalid_admins:
        raise RuntimeError(f"ADMIN_IDS contains non-numeric values: {invalid_admins}")
    admin_ids = {int(value) for value in admin_values}
    db_path = os.getenv("DATABASE_PATH", "data/hariston.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return Settings(bot_token=token, admin_ids=admin_ids, database_path=db_path)


settings = load_settings()
