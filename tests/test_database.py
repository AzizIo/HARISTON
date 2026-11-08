import pytest


@pytest.mark.asyncio
async def test_register_user_is_idempotent_and_creates_referral_code(initialized_db):
    db = initialized_db
    first_code = await db.register_user(101, "alice", "Alice")
    second_code = await db.register_user(101, "alice_new", "Alice Updated")

    assert first_code == second_code
    assert await db.get_referral_code(101) == first_code
    assert await db.get_stats() == (1, 0)


@pytest.mark.asyncio
async def test_referral_is_attributed_only_to_new_user(initialized_db):
    db = initialized_db
    inviter_code = await db.register_user(101, "inviter", "Inviter")
    await db.register_user(202, "friend", "Friend", inviter_code)

    assert await db.get_referral_stats(101) == 1
    await db.register_user(202, "friend2", "Friend Updated")
    assert await db.get_referral_stats(101) == 1


@pytest.mark.asyncio
async def test_invalid_and_self_referrals_are_ignored(initialized_db):
    db = initialized_db
    own_code = await db.register_user(101, "user", "User", "unknown")
    await db.register_user(202, "other", "Other", own_code)
    self_code = await db.register_user(303, "self", "Self")
    await db.register_user(303, "self", "Self", self_code)

    assert await db.get_referral_stats(101) == 1
    assert await db.get_referral_stats(303) == 0


@pytest.mark.asyncio
async def test_notification_preferences_have_defaults_and_can_be_changed(initialized_db):
    db = initialized_db
    await db.register_user(101, "user", "User")

    assert await db.get_notification_preferences(101) == {
        "news": True, "announcements": True, "media": True
    }
    await db.set_notification_preference(101, "media", False)
    assert await db.get_notification_preferences(101) == {
        "news": True, "announcements": True, "media": False
    }
    assert await db.get_user_ids(notifications_only=True, category="media") == []
    assert await db.get_user_ids(notifications_only=True, category="news") == [101]


@pytest.mark.asyncio
async def test_notification_category_is_validated(initialized_db):
    with pytest.raises(ValueError, match="Unsupported"):
        await initialized_db.set_notification_preference(101, "unknown", True)


@pytest.mark.asyncio
async def test_news_can_be_updated_and_deleted(initialized_db):
    db = initialized_db
    news_id = await db.add_news("Old", "Old body", 1001)
    assert await db.update_news(news_id, "New", "New body") is True
    items = await db.get_news()
    assert items[0]["title"] == "New"
    assert await db.delete_news(news_id) is True
    assert await db.delete_news(news_id) is False


@pytest.mark.asyncio
async def test_broadcast_history_is_persisted(initialized_db):
    db = initialized_db
    await db.record_broadcast(1001, 5, 3, 1, 1)
    rows = await db.get_broadcast_history()
    assert len(rows) == 1
    assert (rows[0]["total"], rows[0]["sent"], rows[0]["blocked"], rows[0]["failed"]) == (5, 3, 1, 1)


@pytest.mark.asyncio
async def test_media_items_are_persisted_and_deleted(initialized_db):
    db = initialized_db
    media_id = await db.add_media_item("Trailer", "telegram-file-id", "video", "First look", 1001)
    items = await db.get_media_items()
    assert len(items) == 1
    assert items[0]["title"] == "Trailer"
    assert items[0]["file_id"] == "telegram-file-id"
    assert await db.delete_media_item(media_id) is True
    assert await db.delete_media_item(media_id) is False


@pytest.mark.asyncio
async def test_media_type_is_validated(initialized_db):
    with pytest.raises(ValueError, match="Unsupported"):
        await initialized_db.add_media_item("Bad", "file", "audio", "", 1001)


@pytest.mark.asyncio
async def test_init_db_migrates_legacy_users_table(tmp_path, monkeypatch):
    import aiosqlite
    from dataclasses import replace
    from app import database
    from app.config import settings

    path = tmp_path / "legacy.db"
    async with aiosqlite.connect(path) as connection:
        await connection.execute(
            """CREATE TABLE users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                notifications_enabled INTEGER NOT NULL DEFAULT 1
            )"""
        )
        await connection.execute(
            "INSERT INTO users VALUES (77, 'legacy', 'Legacy', '2026-01-01', 1)"
        )
        await connection.commit()

    monkeypatch.setattr(database, "settings", replace(settings, database_path=str(path)))
    await database.init_db()
    code = await database.register_user(77, "legacy", "Legacy")
    assert code
    assert await database.get_referral_code(77) == code


@pytest.mark.asyncio
async def test_site_settings_are_upserted(initialized_db):
    db = initialized_db
    await db.set_site_setting("about", "First")
    await db.set_site_setting("about", "Updated")
    assert await db.get_site_setting("about") == "Updated"
    assert await db.get_site_setting("missing", "fallback") == "fallback"


@pytest.mark.asyncio
async def test_other_content_types_can_be_deleted(initialized_db):
    db = initialized_db
    channel_id = await db.add_channel("Official", "https://t.me/example", "")
    lesson_id = await db.add_lesson("Guide", "Body", "Basics")
    member_id = await db.add_team_member("Alex", "Developer", "", "", "team-photo-file")
    assert await db.delete_channel(channel_id)
    assert await db.delete_lesson(lesson_id)
    assert await db.delete_team_member(member_id)


@pytest.mark.asyncio
async def test_team_photo_is_optional_and_persisted(initialized_db):
    db = initialized_db
    await db.add_team_member("No Photo", "Tester", "", "")
    await db.add_team_member("With Photo", "Artist", "", "", "photo-file-id")
    members = await db.get_team()
    assert members[0]["photo_file_id"] == "photo-file-id"
    assert members[1]["photo_file_id"] is None
