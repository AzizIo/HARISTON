from types import SimpleNamespace

import pytest

from app.database import (
    add_required_channel,
    delete_required_channel,
    get_required_channels,
)
from app.services.subscriptions import get_missing_required_channels


@pytest.mark.asyncio
async def test_required_channels_can_be_created_listed_and_deleted(initialized_db):
    first = await add_required_channel(
        "Official", "-1001234567890", "https://t.me/official"
    )
    second = await add_required_channel(
        "News", "-1001234567891", "https://t.me/news"
    )

    channels = await get_required_channels()
    assert [item["id"] for item in channels] == [first, second]
    assert channels[0]["chat_id"] == "-1001234567890"
    assert await delete_required_channel(first) is True
    assert await delete_required_channel(first) is False
    assert [item["id"] for item in await get_required_channels()] == [second]


@pytest.mark.asyncio
async def test_membership_gate_accepts_members_and_returns_unjoined_channels(initialized_db):
    await add_required_channel("Joined", "-1001234567890", "https://t.me/joined")
    await add_required_channel("Not joined", "-1001234567891", "https://t.me/not_joined")

    class FakeBot:
        async def get_chat_member(self, chat_id, user_id):
            status = "member" if chat_id == "-1001234567890" else "left"
            return SimpleNamespace(status=status)

    missing = await get_missing_required_channels(FakeBot(), 42)
    assert len(missing) == 1
    assert missing[0]["title"] == "Not joined"


@pytest.mark.asyncio
async def test_membership_gate_accepts_restricted_member(initialized_db):
    await add_required_channel("Restricted", "-1001234567890", "https://t.me/restricted")

    class FakeBot:
        async def get_chat_member(self, chat_id, user_id):
            return SimpleNamespace(status="restricted", is_member=True)

    assert await get_missing_required_channels(FakeBot(), 42) == []
