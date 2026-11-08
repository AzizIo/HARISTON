from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.database import get_required_channels

logger = logging.getLogger(__name__)

MEMBER_STATUSES = {"creator", "administrator", "member"}


async def get_missing_required_channels(bot: Bot, user_id: int) -> list[dict]:
    """Return configured channels the user has not joined.

    Telegram only guarantees getChatMember for other users when the bot is
    an administrator in the target channel. Configuration flow enforces this.
    """
    channels = await get_required_channels()
    missing = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel["chat_id"], user_id)
            is_member = member.status in MEMBER_STATUSES or (
                member.status == "restricted" and getattr(member, "is_member", False)
            )
            if not is_member:
                missing.append(dict(channel))
        except TelegramAPIError:
            logger.exception(
                "Could not verify membership in required channel %s",
                channel["chat_id"],
            )
            # Fail closed: do not grant access if a configured channel cannot
            # be checked. The admin can fix bot permissions/channel settings.
            missing.append(dict(channel))
    return missing


def required_channels_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(
            text=f"➕ {channel['title'][:45]}",
            url=channel["invite_url"],
        )
    builder.button(text="🔄 Проверить подписку", callback_data="sub:check")
    builder.adjust(1)
    return builder.as_markup()



class RequiredSubscriptionMiddleware(BaseMiddleware):
    """Block user-facing callbacks until all mandatory channel memberships exist."""

    async def __call__(self, handler, event, data):
        if isinstance(event, CallbackQuery) and event.data == "sub:check":
            return await handler(event, data)
        user = getattr(event, "from_user", None)
        if user is None or user.id in settings.admin_ids:
            return await handler(event, data)
        missing = await get_missing_required_channels(data["bot"], user.id)
        if not missing:
            return await handler(event, data)

        message = (
            "🔐 <b>Доступ к HARISTON</b>\\n\\n"
            "Чтобы пользоваться ботом, подпишитесь на все каналы ниже, "
            "а затем нажмите «Проверить подписку»."
        )
        if isinstance(event, CallbackQuery):
            if event.message:
                try:
                    await event.message.edit_text(
                        message, reply_markup=required_channels_keyboard(missing)
                    )
                except TelegramAPIError:
                    await event.message.answer(
                        message, reply_markup=required_channels_keyboard(missing)
                    )
            await event.answer("Сначала подпишитесь на обязательные каналы.", show_alert=True)
            return None
        return await handler(event, data)
