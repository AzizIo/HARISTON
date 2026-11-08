import aiosqlite
from datetime import datetime, timezone

from app.config import settings


async def init_db() -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                notifications_enabled INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                is_published INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Общее'
            );
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                contact_url TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        await db.commit()


async def register_user(telegram_id: int, username: str | None, full_name: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO users (telegram_id, username, full_name, joined_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username,
               full_name=excluded.full_name""",
            (telegram_id, username, full_name, now),
        )
        await db.commit()


async def add_news(title: str, body: str, admin_id: int) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            "INSERT INTO news (title, body, created_by, created_at) VALUES (?, ?, ?, ?)",
            (title, body, admin_id, now),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_news(limit: int = 10):
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, title, body, created_at FROM news WHERE is_published=1 ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def add_channel(title: str, url: str, description: str) -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            "INSERT INTO channels (title, url, description) VALUES (?, ?, ?)",
            (title, url, description),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_channels():
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels ORDER BY id DESC")
        return await cursor.fetchall()


async def add_lesson(title: str, body: str, category: str) -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            "INSERT INTO lessons (title, body, category) VALUES (?, ?, ?)",
            (title, body, category),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_lessons():
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM lessons ORDER BY id DESC")
        return await cursor.fetchall()


async def add_team_member(name: str, role: str, description: str, contact_url: str) -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            "INSERT INTO team_members (name, role, description, contact_url) VALUES (?, ?, ?, ?)",
            (name, role, description, contact_url),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_team():
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM team_members ORDER BY id DESC")
        return await cursor.fetchall()


async def get_user_ids(notifications_only: bool = False) -> list[int]:
    async with aiosqlite.connect(settings.database_path) as db:
        query = "SELECT telegram_id FROM users"
        if notifications_only:
            query += " WHERE notifications_enabled=1"
        cursor = await db.execute(query)
        return [row[0] for row in await cursor.fetchall()]


async def get_stats() -> tuple[int, int]:
    async with aiosqlite.connect(settings.database_path) as db:
        users = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        news = await (await db.execute("SELECT COUNT(*) FROM news WHERE is_published=1")).fetchone()
        return int(users[0]), int(news[0])


async def toggle_notifications(telegram_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        row = await (await db.execute(
            "SELECT notifications_enabled FROM users WHERE telegram_id=?", (telegram_id,)
        )).fetchone()
        enabled = not bool(row[0]) if row else True
        await db.execute(
            "UPDATE users SET notifications_enabled=? WHERE telegram_id=?",
            (int(enabled), telegram_id),
        )
        await db.commit()
        return enabled


async def log_admin_action(admin_id: int, action: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, created_at) VALUES (?, ?, ?)",
            (admin_id, action, now),
        )
        await db.commit()
