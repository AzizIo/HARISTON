
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import (
    add_channel, add_lesson, add_news, add_team_member, add_media_item, get_news, get_stats,
    get_user_ids, log_admin_action, record_broadcast,
)
from app.keyboards import admin_flow_menu, admin_menu, broadcast_confirmation, broadcast_category_menu
from app.services.broadcast import send_broadcast
from app.states import AdminFlow

router = Router(name="admin")

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def deny(message: Message) -> None:
    await message.answer("⛔ У вас нет доступа к этому разделу.")


@router.message(F.text == "/admin")
async def admin_command(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await deny(message)
        return
    await message.answer("<b>⚙️ HARISTON · Панель управления</b>\n\nВыберите нужное действие:", reply_markup=admin_menu())


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>⚙️ HARISTON · Панель управления</b>\n\nВыберите нужное действие:",
        reply_markup=admin_menu(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:"))
async def admin_actions(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    action = callback.data.split(":", 1)[1]
    if action == "home":
        return
    if action == "broadcast_send":
        data = await state.get_data()
        draft = data.get("broadcast_text", "")
        if not draft:
            await state.clear()
            await callback.answer("Черновик рассылки не найден", show_alert=True)
            return
        await state.clear()
        category = data.get("broadcast_category", "announcements")
        recipients = await get_user_ids(notifications_only=True, category=category)
        status = await callback.message.edit_text(
            f"📣 <b>Рассылка запущена</b>\n\nПолучателей: {len(recipients)}. Это может занять некоторое время."
        )
        result = await send_broadcast(callback.bot, recipients, draft)
        await record_broadcast(callback.from_user.id, result.total, result.sent, result.blocked, result.failed)
        await log_admin_action(
            callback.from_user.id,
            f"broadcast:{category}:total={result.total},sent={result.sent},blocked={result.blocked},failed={result.failed}",
        )
        await status.edit_text(
            "<b>Рассылка завершена</b>\n\n"
            f"👥 Получателей: {result.total}\n"
            f"✅ Доставлено: {result.sent}\n"
            f"🚫 Недоступны: {result.blocked}\n"
            f"⚠️ Ошибки: {result.failed}",
            reply_markup=admin_menu(),
        )
        await callback.answer("Рассылка завершена")
        return
    if action == "broadcast_cancel":
        await state.clear()
        await callback.message.edit_text("Рассылка отменена.", reply_markup=admin_menu())
        await callback.answer("Отменено")
        return
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("<b>⚙️ HARISTON · Панель управления</b>\n\nДействие отменено. Выберите следующий шаг:", reply_markup=admin_menu())
        await callback.answer("Отменено")
        return
    if action == "stats":
        users, news_count = await get_stats()
        await callback.message.edit_text(
            f"<b>📊 Статистика HARISTON</b>\n\n👥 Пользователей: <b>{users}</b>\n📰 Опубликовано новостей: <b>{news_count}</b>",
            reply_markup=admin_menu(),
        )
    elif action == "users":
        users = await get_user_ids()
        await callback.message.edit_text(
            f"<b>👥 Пользователи</b>\n\nВсего зарегистрировано: <b>{len(users)}</b>",
            reply_markup=admin_menu(),
        )
    elif action == "news_new":
        await state.set_state(AdminFlow.news_title)
        await callback.message.edit_text("📰 <b>Новая публикация</b>\n\nОтправьте заголовок новости.", reply_markup=admin_flow_menu())
    elif action == "news_list":
        items = await get_news(10)
        text = "<b>📰 Последние публикации</b>\n\n" + (
            "\n\n".join(f"<b>#{item['id']} · {item['title']}</b>\n{item['body'][:250]}" for item in items)
            if items else "Новостей пока нет."
        )
        await callback.message.edit_text(text, reply_markup=admin_menu())
    elif action == "channel_new":
        await state.set_state(AdminFlow.channel_title)
        await callback.message.edit_text("📢 <b>Добавление канала</b>\n\nОтправьте название канала.", reply_markup=admin_flow_menu())
    elif action == "lesson_new":
        await state.set_state(AdminFlow.lesson_title)
        await callback.message.edit_text("🎓 <b>Новый обучающий материал</b>\n\nОтправьте название урока.", reply_markup=admin_flow_menu())
    elif action == "media_new":
        await state.set_state(AdminFlow.media_title)
        await callback.message.edit_text("🎬 <b>HARISTON MEDIA</b>\n\nОтправьте название материала.", reply_markup=admin_flow_menu())
    elif action == "team_new":
        await state.set_state(AdminFlow.team_name)
        await callback.message.edit_text("👤 <b>Новый участник команды</b>\n\nОтправьте имя или псевдоним.", reply_markup=admin_flow_menu())
    elif action == "broadcast":
        await state.clear()
        await callback.message.edit_text(
            "📣 <b>Новая рассылка</b>\n\nВыберите категорию получателей:",
            reply_markup=broadcast_category_menu(),
        )
    elif action.startswith("broadcast_category_"):
        category = action.removeprefix("broadcast_category_")
        if category not in {"news", "announcements", "media"}:
            await callback.answer("Неизвестная категория", show_alert=True)
            return
        await state.update_data(broadcast_category=category)
        await state.set_state(AdminFlow.broadcast_text)
        await callback.message.edit_text(
            f"📣 <b>Рассылка · {category}</b>\n\nОтправьте текст сообщения. Перед отправкой будет показан предпросмотр.",
            reply_markup=admin_flow_menu(),
        )
    await callback.answer()


@router.message(AdminFlow.news_title)
async def receive_news_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    title = (message.text or "").strip()
    if not title or len(title) > 180:
        await message.answer("Заголовок должен содержать от 1 до 180 символов. Попробуйте ещё раз.")
        return
    await state.update_data(news_title=title)
    await state.set_state(AdminFlow.news_body)
    await message.answer("Теперь отправьте текст новости. Для отмены используйте /cancel.")


@router.message(AdminFlow.news_body)
async def receive_news_body(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    body = (message.text or message.caption or "").strip()
    if not body:
        await message.answer("Текст новости не должен быть пустым. Отправьте текст ещё раз.")
        return
    data = await state.get_data()
    news_id = await add_news(data["news_title"], body, message.from_user.id)
    await log_admin_action(message.from_user.id, f"published_news:{news_id}")
    await state.clear()
    await message.answer(f"✅ Новость <b>#{news_id}</b> опубликована и доступна в разделе «Новости».")


@router.message(AdminFlow.channel_title)
async def channel_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    await state.update_data(channel_title=(message.text or "").strip())
    await state.set_state(AdminFlow.channel_url)
    await message.answer("Отправьте ссылку на канал (https://t.me/...).")


@router.message(AdminFlow.channel_url)
async def channel_url(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    url = (message.text or "").strip()
    if not url.startswith(("https://t.me/", "https://")):
        await message.answer("Нужна корректная ссылка, начинающаяся с https://")
        return
    await state.update_data(channel_url=url)
    await state.set_state(AdminFlow.channel_description)
    await message.answer("Добавьте короткое описание канала.")


@router.message(AdminFlow.channel_description)
async def channel_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    data = await state.get_data()
    item_id = await add_channel(data["channel_title"], data["channel_url"], (message.text or "").strip())
    await log_admin_action(message.from_user.id, f"added_channel:{item_id}")
    await state.clear()
    await message.answer("✅ Канал добавлен в раздел «Наши каналы».")


@router.message(AdminFlow.lesson_title)
async def lesson_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    await state.update_data(lesson_title=(message.text or "").strip())
    await state.set_state(AdminFlow.lesson_category)
    await message.answer("Укажите категорию материала (например: Начало игры, Экономика, Правила).")


@router.message(AdminFlow.lesson_category)
async def lesson_category(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    await state.update_data(lesson_category=(message.text or "Общее").strip())
    await state.set_state(AdminFlow.lesson_body)
    await message.answer("Отправьте текст обучающего материала.")


@router.message(AdminFlow.lesson_body)
async def lesson_body(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    data = await state.get_data()
    item_id = await add_lesson(data["lesson_title"], (message.text or "").strip(), data["lesson_category"])
    await log_admin_action(message.from_user.id, f"added_lesson:{item_id}")
    await state.clear()
    await message.answer("✅ Материал добавлен в раздел «Обучение».")


@router.message(AdminFlow.team_name)
async def team_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    await state.update_data(team_name=(message.text or "").strip())
    await state.set_state(AdminFlow.team_role)
    await message.answer("Укажите должность или роль в проекте.")


@router.message(AdminFlow.team_role)
async def team_role(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    await state.update_data(team_role=(message.text or "").strip())
    await state.set_state(AdminFlow.team_description)
    await message.answer("Кратко опишите обязанности или информацию об участнике.")


@router.message(AdminFlow.team_description)
async def team_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    await state.update_data(team_description=(message.text or "").strip())
    await state.set_state(AdminFlow.team_contact)
    await message.answer("Отправьте ссылку для связи (например https://t.me/username) или символ - если ссылки нет.")


@router.message(AdminFlow.team_contact)
async def team_contact(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    data = await state.get_data()
    contact = (message.text or "").strip()
    if contact == "-":
        contact = ""
    item_id = await add_team_member(
        data["team_name"], data["team_role"], data["team_description"], contact
    )
    await log_admin_action(message.from_user.id, f"added_team_member:{item_id}")
    await state.clear()
    await message.answer("✅ Участник добавлен в раздел «Команда».")


@router.message(AdminFlow.broadcast_text)
async def receive_broadcast(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        await message.answer("Сообщение не должно быть пустым. Попробуйте ещё раз.")
        return
    await state.update_data(broadcast_text=text)
    data = await state.get_data()
    category = data.get("broadcast_category", "announcements")
    recipients = await get_user_ids(notifications_only=True, category=category)
    await state.set_state(AdminFlow.broadcast_confirm)
    await message.answer(
        "<b>Предпросмотр рассылки</b>\n\n"
        f"{text[:3000]}\n\n"
        f"Категория: <b>{category}</b>\n"
        f"Категория: <b>{category}</b>\n"
        f"Получателей с включёнными уведомлениями: <b>{len(recipients)}</b>\n\n"
        "Отправить сообщение всем выбранным пользователям?",
        reply_markup=broadcast_confirmation(),
    )


@router.message(F.text == "/cancel")
async def cancel_flow(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Действие отменено. Откройте /admin для возврата в панель.")


@router.message(AdminFlow.media_title)
async def media_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    title = (message.text or "").strip()
    if not title or len(title) > 180:
        await message.answer("Название должно содержать от 1 до 180 символов.")
        return
    await state.update_data(media_title=title)
    await state.set_state(AdminFlow.media_upload)
    await message.answer("Отправьте фото, видео или документ. Подпись к файлу необязательна.")


@router.message(AdminFlow.media_upload)
async def media_upload(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await deny(message)
        return
    file_id = None
    media_type = None
    if message.photo:
        file_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video:
        file_id, media_type = message.video.file_id, "video"
    elif message.document:
        file_id, media_type = message.document.file_id, "document"
    if not file_id or not media_type:
        await message.answer("Нужен файл: фото, видео или документ.")
        return
    data = await state.get_data()
    media_id = await add_media_item(
        data["media_title"], file_id, media_type,
        (message.caption or "").strip(), message.from_user.id,
    )
    await log_admin_action(message.from_user.id, f"added_media:{media_id}")
    await state.clear()
    await message.answer(f"✅ Материал HARISTON MEDIA #{media_id} добавлен.")
