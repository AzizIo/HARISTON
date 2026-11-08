from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import get_news, register_user
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


@router.callback_query(F.data.startswith("menu:"))
async def static_sections(callback: CallbackQuery) -> None:
    section = callback.data.split(":", 1)[1]
    pages = {
        "about": "<b>🌍 О проекте HARISTON</b>\n\nИнформация о концепции, мире и планах проекта скоро появится здесь.",
        "channels": "<b>📢 Официальные каналы</b>\n\nСписок ресурсов будет добавлен администрацией.",
        "education": "<b>📚 Обучение</b>\n\nГайды и обучающие материалы появятся здесь.",
        "team": "<b>👥 Команда HARISTON</b>\n\nКарточки участников команды скоро появятся здесь.",
        "contact": "<b>💬 Связаться с командой</b>\n\nКонтакты администрации будут опубликованы здесь.",
        "notifications": "<b>🔔 Уведомления</b>\n\nВ этой версии включены важные новости сообщества. Настройки категорий добавим следующим этапом.",
    }
    await callback.message.edit_text(pages.get(section, "Раздел не найден."), reply_markup=back_menu())
    await callback.answer()
