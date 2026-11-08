import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import add_news, get_stats, get_user_ids, log_admin_action
from app.keyboards import admin_menu, back_menu
from app.states import AdminFlow

router = Router(name="admin")
logger = logging.getLogger(__name__)


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
    if action == "stats":
        users, news = await get_stats()
        await callback.message.edit_text(
            f"<b>📊 Статистика HARISTON</b>\n\n👥 Пользователей: <b>{users}</b>\n📰 Опубликовано новостей: <b>{news}</b>",
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
        await callback.message.edit_text("<b>📰 Новая публикация</b>\n\nОтправьте заголовок новости.", reply_markup=back_menu())
    elif action == "news_list":
        from app.database import get_news
        items = await get_news(10)
        if items:
            text = "<b>📰 Последние публикации</b>\n\n" + "\n\n".join(
                f"<b>#{item['id']} · {item['title']}</b>\n{item['body'][:250]}" for item in items
            )
        else:
            text = "<b>📰 Публикации</b>\n\nНовостей пока нет."
        await callback.message.edit_text(text, reply_markup=admin_menu())
    elif action == "broadcast":
        await state.set_state(AdminFlow.broadcast_text)
        await callback.message.edit_text(
            "<b>📣 Рассылка</b>\n\nОтправьте текст сообщения. Оно будет разослано всем зарегистрированным пользователям, которые не заблокировали бота.",
            reply_markup=back_menu(),
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
    await state.clear()
    user_ids = await get_user_ids()
    sent = failed = 0
    status = await message.answer(f"📣 Начинаю рассылку для {len(user_ids)} пользователей…")
    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, text)
            sent += 1
        except Exception as exc:
            failed += 1
            logger.warning("Broadcast to %s failed: %s", user_id, exc)
        await asyncio.sleep(0.05)
    await log_admin_action(message.from_user.id, f"broadcast:sent={sent},failed={failed}")
    await status.edit_text(f"<b>Рассылка завершена</b>\n\n✅ Доставлено: {sent}\n⚠️ Не доставлено: {failed}")


@router.message(F.text == "/cancel")
async def cancel_flow(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Действие отменено. Откройте /admin для возврата в панель.")
