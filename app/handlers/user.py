from html import escape
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import (
    get_channels, get_lessons, get_news, get_team, get_media_items, register_user,
    get_notification_preferences, set_notification_preference,
    get_referral_stats,
)
from app.keyboards import back_menu, main_menu, notification_menu

router = Router(name="user")

WELCOME = (
    "<b>HARISTON — больше, чем игра.</b>\n\n"
    "Добро пожаловать в официальное сообщество проекта! Здесь собраны новости, "
    "обучение, полезные ресурсы и контакты команды.\n\n"
    "Присоединяйся к сообществу и следи за развитием HARISTON."
)


@router.message(CommandStart())
async def start(message: Message) -> None:
    user = message.from_user
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""
    invite_code = payload.removeprefix("ref_") if payload.startswith("ref_") else None
    await register_user(user.id, user.username, user.full_name, invite_code)
    await message.answer(WELCOME, reply_markup=main_menu(user.id in settings.admin_ids))


@router.callback_query(F.data == "menu:home")
async def home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        WELCOME,
        reply_markup=main_menu(callback.from_user.id in settings.admin_ids),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:news")
async def news(callback: CallbackQuery) -> None:
    items = await get_news(10)
    if not items:
        text = "<b>📰 Новости HARISTON</b>\n\nПока публикаций нет. Заглядывай позже!"
    else:
        parts = ["<b>📰 Новости HARISTON</b>"]
        for item in items:
            parts.append(f"\n<b>#{item['id']} · {escape(item['title'])}</b>\n{escape(item['body'][:700])}")
        text = "\n".join(parts)
    await callback.message.edit_text(text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:channels")
async def channels(callback: CallbackQuery) -> None:
    items = await get_channels()
    if items:
        text = "<b>📢 Официальные каналы HARISTON</b>\n\n" + "\n\n".join(
            f"<b>{escape(item['title'])}</b>\n{escape(item['description'])}\n<a href=\"{escape(item['url'], quote=True)}\">Перейти к каналу</a>"
            for item in items
        )
    else:
        text = "<b>📢 Официальные каналы</b>\n\nСписок ресурсов скоро появится."
    await callback.message.edit_text(text, reply_markup=back_menu(), disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "menu:education")
async def education(callback: CallbackQuery) -> None:
    items = await get_lessons()
    if items:
        text = "<b>📚 Обучение HARISTON</b>\n\n" + "\n\n".join(
            f"<b>{escape(item['title'])}</b> · <i>{escape(item['category'])}</i>\n{escape(item['body'][:900])}"
            for item in items
        )
    else:
        text = "<b>📚 Обучение</b>\n\nОбучающие материалы скоро появятся."
    await callback.message.edit_text(text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:team")
async def team(callback: CallbackQuery) -> None:
    items = await get_team()
    if items:
        blocks = []
        for item in items:
            contact = f"\n<a href=\"{escape(item['contact_url'], quote=True)}\">Связаться</a>" if item["contact_url"] else ""
            blocks.append(f"<b>{escape(item['name'])}</b>\n{escape(item['role'])}\n{escape(item['description'])}{contact}")
        text = "<b>👥 Команда HARISTON</b>\n\n" + "\n\n".join(blocks)
    else:
        text = "<b>👥 Команда HARISTON</b>\n\nКарточки команды скоро появятся."
    await callback.message.edit_text(text, reply_markup=back_menu(), disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "menu:notifications")
async def notifications(callback: CallbackQuery) -> None:
    preferences = await get_notification_preferences(callback.from_user.id)
    await callback.message.edit_text(
        "<b>🔔 Настройки уведомлений</b>\n\nВыберите, какие сообщения HARISTON вы хотите получать:",
        reply_markup=notification_menu(preferences),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("prefs:"))
async def toggle_notification_category(callback: CallbackQuery) -> None:
    category = callback.data.split(":", 1)[1]
    preferences = await get_notification_preferences(callback.from_user.id)
    if category not in preferences:
        await callback.answer("Неизвестная категория", show_alert=True)
        return
    enabled = not preferences[category]
    await set_notification_preference(callback.from_user.id, category, enabled)
    preferences[category] = enabled
    await callback.message.edit_reply_markup(reply_markup=notification_menu(preferences))
    await callback.answer("Настройка обновлена")


@router.callback_query(F.data == "menu:referral")
async def referral(callback: CallbackQuery) -> None:
    code = await register_user(
        callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )
    referrals = await get_referral_stats(callback.from_user.id)
    bot_user = await callback.bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=ref_{code}"
    await callback.message.edit_text(
        "<b>🤝 Приглашай друзей в HARISTON</b>\n\n"
        f"Твоя персональная ссылка:\n<code>{link}</code>\n\n"
        f"Приглашено пользователей: <b>{referrals}</b>",
        reply_markup=back_menu(),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"menu:about", "menu:contact"}))
async def static_sections(callback: CallbackQuery) -> None:
    section = callback.data.split(":", 1)[1]
    pages = {
        "about": "<b>🌍 О проекте HARISTON</b>\n\nИнформация о концепции, мире и планах проекта скоро появится здесь.",
        "contact": "<b>💬 Связаться с командой</b>\n\nКонтакты администрации будут опубликованы здесь.",
    }
    await callback.message.edit_text(pages.get(section, "Раздел не найден."), reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:media")
async def media(callback: CallbackQuery) -> None:
    items = await get_media_items(10)
    if not items:
        await callback.message.edit_text(
            "<b>🎬 HARISTON MEDIA</b>\n\nВидео, изображения и материалы проекта появятся здесь.",
            reply_markup=back_menu(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "<b>🎬 HARISTON MEDIA</b>\n\nПоследние материалы отправлены ниже.",
        reply_markup=back_menu(),
    )
    for item in reversed(items):
        caption = f"<b>{escape(item['title'])}</b>"
        if item["caption"]:
            caption += f"\n{escape(item['caption'])}"
        if item["media_type"] == "photo":
            await callback.message.answer_photo(item["file_id"], caption=caption)
        elif item["media_type"] == "video":
            await callback.message.answer_video(item["file_id"], caption=caption)
        else:
            await callback.message.answer_document(item["file_id"], caption=caption)
    await callback.answer()
