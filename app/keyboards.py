from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Custom emoji IDs from the NEWS EMOJI pack used in the project's Telegram assets.
EMOJI = {
    "news": "5287767094052543762",
    "info": "5404515205784806076",
    "channels": "5264710902153767489",
    "education": "5404515205784806076",
    "team": "6271387924223234127",
    "contact": "5985596818912712352",
    "notifications": "5217881018299595934",
    "stats": "5897792062291449826",
    "create": "5350486389806868244",
    "list": "5287767094052543762",
    "add": "5350486389806868244",
    "broadcast": "5264710902153767489",
    "users": "6271387924223234127",
    "settings": "5341715473882955310",
    "cancel": "5985346521103604145",
    "back": "5404515205784806076",
}


def _button(kb: InlineKeyboardBuilder, text: str, callback: str,
            emoji: str | None = None, style: str | None = None) -> None:
    options = {"text": text, "callback_data": callback}
    if emoji:
        options["icon_custom_emoji_id"] = EMOJI[emoji]
    if style:
        options["style"] = style
    kb.button(**options)


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    items = [
        ("Новости", "menu:news", "news", "primary"),
        ("О проекте", "menu:about", "info", None),
        ("Наши каналы", "menu:channels", "channels", "primary"),
        ("Обучение", "menu:education", "education", "primary"),
        ("HARISTON MEDIA", "menu:media", "broadcast", "primary"),
        ("Команда", "menu:team", "team", None),
        ("Связаться", "menu:contact", "contact", "success"),
        ("Уведомления", "menu:notifications", "notifications", None),
        ("Пригласить друга", "menu:referral", "contact", None),
    ]
    for text, callback, emoji, style in items:
        _button(kb, text, callback, emoji, style)
    kb.adjust(2, 2, 2, 1)
    if is_admin:
        _button(kb, "Админ-панель", "admin:home", "settings", "primary")
        kb.adjust(2, 2, 2, 1, 1)
    return kb.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _button(kb, "Главное меню", "menu:home", "back")
    return kb.as_markup()


def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    items = [
        ("Статистика", "admin:stats", "stats", "primary"),
        ("Создать новость", "admin:news_new", "create", "success"),
        ("Последние новости", "admin:news_list", "list", "primary"),
        ("Добавить канал", "admin:channel_new", "add", "primary"),
        ("Добавить урок", "admin:lesson_new", "education", "primary"),
        ("Добавить медиа", "admin:media_new", "broadcast", "primary"),
        ("Добавить сотрудника", "admin:team_new", "team", None),
        ("Рассылка", "admin:broadcast", "broadcast", "success"),
        ("Пользователи", "admin:users", "users", None),
        ("Главное меню", "menu:home", "back", None),
    ]
    for text, callback, emoji, style in items:
        _button(kb, text, callback, emoji, style)
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup()


def admin_flow_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _button(kb, "Отменить действие", "admin:cancel", "cancel", "danger")
    return kb.as_markup()


def broadcast_confirmation() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _button(kb, "Подтвердить рассылку", "admin:broadcast_send", "create", "success")
    _button(kb, "Отменить", "admin:broadcast_cancel", "cancel", "danger")
    kb.adjust(1, 1)
    return kb.as_markup()


def notification_menu(preferences: dict[str, bool]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    labels = {
        "news": "Новости",
        "announcements": "Анонсы",
        "media": "HARISTON MEDIA",
    }
    for category, label in labels.items():
        state = "Вкл." if preferences.get(category, True) else "Выкл."
        _button(kb, f"{label}: {state}", f"prefs:{category}", "notifications",
                "success" if preferences.get(category, True) else "danger")
    _button(kb, "Главное меню", "menu:home", "back")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def broadcast_category_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _button(kb, "Новости", "admin:broadcast_category_news", "news", "primary")
    _button(kb, "Анонсы", "admin:broadcast_category_announcements", "info", "success")
    _button(kb, "HARISTON MEDIA", "admin:broadcast_category_media", "education", "primary")
    _button(kb, "Назад в панель", "admin:home", "back")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()
