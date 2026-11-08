from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BroadcastResult:
    total: int
    sent: int
    blocked: int
    failed: int

    @property
    def not_sent(self) -> int:
        return self.total - self.sent


async def _deliver(bot: Bot, chat_id: int, text: str, parse_mode: str | None) -> str:
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return "sent"
    except TelegramForbiddenError:
        return "blocked"
    except TelegramBadRequest as exc:
        # A deleted account or inaccessible chat is not a transient failure.
        logger.info("Broadcast recipient %s is unavailable: %s", chat_id, exc)
        return "blocked"
    except TelegramRetryAfter as exc:
        # Telegram explicitly tells us when this recipient may be retried.
        await asyncio.sleep(min(float(exc.retry_after) + 0.2, 30.0))
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return "sent"
        except (TelegramForbiddenError, TelegramBadRequest):
            return "blocked"
        except Exception:
            logger.exception("Broadcast retry failed for recipient %s", chat_id)
            return "failed"
    except (TelegramNetworkError, TelegramServerError):
        logger.exception("Telegram temporarily failed for recipient %s", chat_id)
        return "failed"
    except Exception:
        logger.exception("Unexpected broadcast error for recipient %s", chat_id)
        return "failed"


async def send_broadcast(
    bot: Bot,
    recipients: list[int],
    text: str,
    *,
    parse_mode: str | None = None,
    concurrency: int = 15,
) -> BroadcastResult:
    """Send a message to a stable recipient snapshot with bounded concurrency."""
    if not text.strip():
        raise ValueError("Broadcast text must not be empty")
    if len(text) > 4096:
        raise ValueError("Broadcast text exceeds Telegram's 4096-character limit")
    if concurrency < 1:
        raise ValueError("Concurrency must be positive")

    unique_recipients = list(dict.fromkeys(recipients))
    semaphore = asyncio.Semaphore(concurrency)

    async def deliver(chat_id: int) -> str:
        async with semaphore:
            return await _deliver(bot, chat_id, text, parse_mode)

    outcomes = await asyncio.gather(*(deliver(chat_id) for chat_id in unique_recipients))
    sent = outcomes.count("sent")
    blocked = outcomes.count("blocked")
    failed = outcomes.count("failed")
    return BroadcastResult(
        total=len(unique_recipients),
        sent=sent,
        blocked=blocked,
        failed=failed,
    )
