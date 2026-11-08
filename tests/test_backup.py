import sqlite3

import pytest

from app.backup import create_backup


def test_backup_creates_restorable_sqlite_snapshot(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('persisted')")

    backup = create_backup(source, tmp_path / "backups")

    assert backup.exists()
    with sqlite3.connect(backup) as connection:
        row = connection.execute("SELECT value FROM sample").fetchone()
    assert row == ("persisted",)


def test_backup_rejects_missing_database(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "missing.db", tmp_path / "backups")


def test_backup_rejects_in_memory_database():
    with pytest.raises(ValueError, match="in-memory"):
        create_backup(":memory:")
