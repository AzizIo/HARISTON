import os
from dataclasses import replace

import pytest
import pytest_asyncio

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("ADMIN_IDS", "1001")
os.environ.setdefault("DATABASE_PATH", "data/test-hariston.db")


@pytest_asyncio.fixture
async def initialized_db(tmp_path, monkeypatch):
    from app import database
    from app.config import settings

    test_settings = replace(settings, database_path=str(tmp_path / "hariston-test.db"))
    monkeypatch.setattr(database, "settings", test_settings)
    await database.init_db()
    return database
