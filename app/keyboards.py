from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    items = [
        ("📰 Новости", "news"), ("🌍 О проекте", "about"),
        ("📢 Наши каналы", "channels"), ("📚 Обучение", "education"),
        ("👥 Команда", "team"), ("💬 Связаться", "contact"),
        ("🔔 Уведомления", "notifications"),
    ]
    for text, callback in items:
        kb.button(text=text, callback_data=f"menu:{callback}")
    kb.adjust(2, 2, 2, 1)
    if is_admin:
        kb.button(text="⚙️ Админ-панель", callback_data="admin:home")
        kb.adjust(2, 2, 2, 1, 1)
    return kb.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Главное меню", callback_data="menu:home")
    return kb.as_markup()


def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for text, data in [
        ("📊 Статистика", "admin:stats"),
        ("📰 Создать новость", "admin:news_new"),
        ("📚 Последние новости", "admin:news_list"),
        ("📢 Добавить канал", "admin:channel_new"),
        ("🎓 Добавить урок", "admin:lesson_new"),
        ("👤 Добавить сотрудника", "admin:team_new"),
        ("📣 Рассылка", "admin:broadcast"),
        ("👥 Пользователи", "admin:users"),
        ("⬅️ Главное меню", "menu:home"),
    ]:
        kb.button(text=text, callback_data=data)
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup()


def admin_flow_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✖️ Отменить действие", callback_data="admin:cancel")
    return kb.as_markup()
