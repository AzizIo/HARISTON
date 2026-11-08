from unittest.mock import AsyncMock

import pytest

from app.services.broadcast import send_broadcast


@pytest.mark.asyncio
async def test_broadcast_counts_successes_and_deduplicates_recipients():
    bot = AsyncMock()
    result = await send_broadcast(bot, [10, 20, 10, 30], "Hello")

    assert (result.total, result.sent, result.blocked, result.failed) == (3, 3, 0, 0)
    assert bot.send_message.await_count == 3


@pytest.mark.asyncio
async def test_broadcast_continues_after_recipient_error():
    bot = AsyncMock()
    bot.send_message.side_effect = [None, RuntimeError("network"), None]

    result = await send_broadcast(bot, [10, 20, 30], "Update", concurrency=1)

    assert result.total == 3
    assert result.sent == 2
    assert result.failed == 1
    assert result.blocked == 0


@pytest.mark.asyncio
async def test_broadcast_rejects_empty_message():
    with pytest.raises(ValueError, match="must not be empty"):
        await send_broadcast(AsyncMock(), [10], "   ")


@pytest.mark.asyncio
async def test_broadcast_rejects_invalid_concurrency():
    with pytest.raises(ValueError, match="positive"):
        await send_broadcast(AsyncMock(), [10], "Hello", concurrency=0)


@pytest.mark.asyncio
async def test_broadcast_empty_recipient_list_is_valid():
    bot = AsyncMock()
    result = await send_broadcast(bot, [], "Hello")

    assert result.total == result.sent == result.blocked == result.failed == 0
    bot.send_message.assert_not_awaited()
