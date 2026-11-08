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


async def log_admin_action(admin_id: int, action: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, created_at) VALUES (?, ?, ?)",
            (admin_id, action, now),
        )
        await db.commit()
