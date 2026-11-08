from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def create_backup(
    source_path: str | Path | None = None,
    backup_dir: str | Path = "backups",
) -> Path:
    """Create a consistent SQLite snapshot using SQLite's online backup API."""
    source = Path(source_path or os.getenv("DATABASE_PATH", "data/hariston.db"))
    if str(source) == ":memory:":
        raise ValueError("An in-memory database cannot be backed up by this command")
    if not source.exists():
        raise FileNotFoundError(f"Database does not exist: {source}")

    destination_dir = Path(backup_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = destination_dir / f"hariston-{timestamp}.sqlite3"

    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)

    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a consistent HARISTON SQLite backup.")
    parser.add_argument("--output-dir", default="backups", help="Directory for backup files")
    args = parser.parse_args()
    print(create_backup(backup_dir=args.output_dir))


if __name__ == "__main__":
    main()
