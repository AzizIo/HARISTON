from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import (
    get_channels, get_lessons, get_news, get_team, register_user, toggle_notifications,
)
from app.keyboards import back_menu, main_menu

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
    await register_user(user.id, user.username, user.full_name)
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
            parts.append(f"\n<b>#{item['id']} · {item['title']}</b>\n{item['body'][:700]}")
        text = "\n".join(parts)
    await callback.message.edit_text(text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:channels")
async def channels(callback: CallbackQuery) -> None:
    items = await get_channels()
    if items:
        text = "<b>📢 Официальные каналы HARISTON</b>\n\n" + "\n\n".join(
            f"<b>{item['title']}</b>\n{item['description']}\n<a href=\"{item['url']}\">Перейти к каналу</a>"
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
            f"<b>{item['title']}</b> · <i>{item['category']}</i>\n{item['body'][:900]}"
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
            contact = f"\n<a href=\"{item['contact_url']}\">Связаться</a>" if item["contact_url"] else ""
            blocks.append(f"<b>{item['name']}</b>\n{item['role']}\n{item['description']}{contact}")
        text = "<b>👥 Команда HARISTON</b>\n\n" + "\n\n".join(blocks)
    else:
        text = "<b>👥 Команда HARISTON</b>\n\nКарточки команды скоро появятся."
    await callback.message.edit_text(text, reply_markup=back_menu(), disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "menu:notifications")
async def notifications(callback: CallbackQuery) -> None:
    enabled = await toggle_notifications(callback.from_user.id)
    state = "включены" if enabled else "отключены"
    await callback.message.edit_text(
        f"<b>🔔 Уведомления {state}</b>\n\nНастройка влияет на будущие информационные рассылки.",
        reply_markup=back_menu(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("menu:"))
async def static_sections(callback: CallbackQuery) -> None:
    section = callback.data.split(":", 1)[1]
    pages = {
        "about": "<b>🌍 О проекте HARISTON</b>\n\nИнформация о концепции, мире и планах проекта скоро появится здесь.",
        "contact": "<b>💬 Связаться с командой</b>\n\nКонтакты администрации будут опубликованы здесь.",
    }
    await callback.message.edit_text(pages.get(section, "Раздел не найден."), reply_markup=back_menu())
    await callback.answer()
