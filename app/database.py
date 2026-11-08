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
                notifications_enabled INTEGER NOT NULL DEFAULT 1,
                referral_code TEXT,
                referred_by INTEGER REFERENCES users(telegram_id)
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
                contact_url TEXT NOT NULL DEFAULT '',
                photo_file_id TEXT
            );
            CREATE TABLE IF NOT EXISTS notification_preferences (
                telegram_id INTEGER NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (telegram_id, category)
            );
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                file_id TEXT NOT NULL,
                media_type TEXT NOT NULL CHECK(media_type IN ('photo', 'video', 'document')),
                caption TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                created_by INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS broadcast_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                total INTEGER NOT NULL,
                sent INTEGER NOT NULL,
                blocked INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        columns = {row[1] for row in await (await db.execute("PRAGMA table_info(users)")).fetchall()}
        if "referral_code" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
        if "referred_by" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER REFERENCES users(telegram_id)")
        team_columns = {row[1] for row in await (await db.execute("PRAGMA table_info(team_members)")).fetchall()}
        if "photo_file_id" not in team_columns:
            await db.execute("ALTER TABLE team_members ADD COLUMN photo_file_id TEXT")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_notifications ON users(notifications_enabled)")
        await db.commit()


async def register_user(
    telegram_id: int,
    username: str | None,
    full_name: str,
    invite_code: str | None = None,
) -> str:
    """Upsert a user and attribute a referral only on the first registration."""
    import secrets

    now = datetime.now(timezone.utc).isoformat()
    own_code = secrets.token_urlsafe(8)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        referrer = None
        if invite_code:
            row = await (await db.execute(
                "SELECT telegram_id FROM users WHERE referral_code=? AND telegram_id<>?",
                (invite_code, telegram_id),
            )).fetchone()
            referrer = int(row[0]) if row else None
        await db.execute(
            """INSERT INTO users
               (telegram_id, username, full_name, joined_at, referral_code, referred_by)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET
               username=excluded.username, full_name=excluded.full_name""",
            (telegram_id, username, full_name, now, own_code, referrer),
        )
        row = await (await db.execute(
            "SELECT referral_code FROM users WHERE telegram_id=?", (telegram_id,)
        )).fetchone()
        code = row[0]
        if not code:
            code = own_code
            await db.execute(
                "UPDATE users SET referral_code=? WHERE telegram_id=?",
                (code, telegram_id),
            )
        await db.commit()
        return str(code)


async def get_referral_stats(telegram_id: int) -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        row = await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by=?", (telegram_id,)
        )).fetchone()
        return int(row[0])


async def get_referral_code(telegram_id: int) -> str | None:
    async with aiosqlite.connect(settings.database_path) as db:
        row = await (await db.execute(
            "SELECT referral_code FROM users WHERE telegram_id=?", (telegram_id,)
        )).fetchone()
        return str(row[0]) if row and row[0] else None


async def set_notification_preference(telegram_id: int, category: str, enabled: bool) -> None:
    allowed = {"news", "announcements", "media"}
    if category not in allowed:
        raise ValueError("Unsupported notification category")
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO notification_preferences (telegram_id, category, enabled)
               VALUES (?, ?, ?)
               ON CONFLICT(telegram_id, category) DO UPDATE SET enabled=excluded.enabled""",
            (telegram_id, category, int(enabled)),
        )
        await db.commit()


async def get_notification_preferences(telegram_id: int) -> dict[str, bool]:
    defaults = {"news": True, "announcements": True, "media": True}
    async with aiosqlite.connect(settings.database_path) as db:
        rows = await (await db.execute(
            "SELECT category, enabled FROM notification_preferences WHERE telegram_id=?",
            (telegram_id,),
        )).fetchall()
    defaults.update({category: bool(enabled) for category, enabled in rows})
    return defaults


async def record_broadcast(
    admin_id: int, total: int, sent: int, blocked: int, failed: int
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO broadcast_logs
               (admin_id, total, sent, blocked, failed, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (admin_id, total, sent, blocked, failed, now),
        )
        await db.commit()


async def get_broadcast_history(limit: int = 10):
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM broadcast_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        return await cursor.fetchall()


async def set_site_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO site_settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value),
        )
        await db.commit()


async def get_site_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(settings.database_path) as db:
        row = await (await db.execute(
            "SELECT value FROM site_settings WHERE key=?", (key,)
        )).fetchone()
        return str(row[0]) if row else default


async def delete_news(news_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute("DELETE FROM news WHERE id=?", (news_id,))
        await db.commit()
        return cursor.rowcount > 0


async def update_news(news_id: int, title: str, body: str) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            "UPDATE news SET title=?, body=? WHERE id=?", (title, body, news_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_channel(channel_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute("DELETE FROM channels WHERE id=?", (channel_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_lesson(lesson_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_team_member(member_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute("DELETE FROM team_members WHERE id=?", (member_id,))
        await db.commit()
        return cursor.rowcount > 0


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


async def add_team_member(
    name: str, role: str, description: str, contact_url: str,
    photo_file_id: str | None = None,
) -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            """INSERT INTO team_members
               (name, role, description, contact_url, photo_file_id)
               VALUES (?, ?, ?, ?, ?)""",
            (name, role, description, contact_url, photo_file_id),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_team():
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM team_members ORDER BY id DESC")
        return await cursor.fetchall()


async def get_user_ids(
    notifications_only: bool = False, category: str | None = None
) -> list[int]:
    async with aiosqlite.connect(settings.database_path) as db:
        if category is not None:
            if category not in {"news", "announcements", "media"}:
                raise ValueError("Unsupported notification category")
            cursor = await db.execute(
                """SELECT u.telegram_id FROM users AS u
                   LEFT JOIN notification_preferences AS p
                     ON p.telegram_id=u.telegram_id AND p.category=?
                   WHERE u.notifications_enabled=1 AND COALESCE(p.enabled, 1)=1""",
                (category,),
            )
        elif notifications_only:
            cursor = await db.execute(
                "SELECT telegram_id FROM users WHERE notifications_enabled=1"
            )
        else:
            cursor = await db.execute("SELECT telegram_id FROM users")
        return [int(row[0]) for row in await cursor.fetchall()]


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


async def add_media_item(
    title: str, file_id: str, media_type: str, caption: str, admin_id: int
) -> int:
    if media_type not in {"photo", "video", "document"}:
        raise ValueError("Unsupported media type")
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute(
            """INSERT INTO media_items
               (title, file_id, media_type, caption, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, file_id, media_type, caption, now, admin_id),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_media_items(limit: int = 10):
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM media_items ORDER BY id DESC LIMIT ?", (limit,)
        )
        return await cursor.fetchall()


async def delete_media_item(media_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cursor = await db.execute("DELETE FROM media_items WHERE id=?", (media_id,))
        await db.commit()
        return cursor.rowcount > 0
