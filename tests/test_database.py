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
    await db.register_user(202, "friend", "Friend", f"ref_{inviter_code}")

    assert await db.get_referral_stats(101) == 1
    await db.register_user(202, "friend2", "Friend Updated")
    assert await db.get_referral_stats(101) == 1


@pytest.mark.asyncio
async def test_invalid_and_self_referrals_are_ignored(initialized_db):
    db = initialized_db
    own_code = await db.register_user(101, "user", "User", "unknown")
    await db.register_user(202, "other", "Other", own_code)
    await db.register_user(303, "self", "Self", own_code)

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
