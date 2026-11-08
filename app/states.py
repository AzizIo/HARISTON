from aiogram.fsm.state import State, StatesGroup


class AdminFlow(StatesGroup):
    news_title = State()
    news_body = State()
    news_edit_title = State()
    news_edit_body = State()
    broadcast_text = State()
    broadcast_confirm = State()
    media_title = State()
    media_upload = State()
    setting_value = State()
    channel_title = State()
    channel_url = State()
    channel_description = State()
    lesson_title = State()
    lesson_category = State()
    lesson_body = State()
    team_name = State()
    team_role = State()
    team_description = State()
    team_contact = State()
    team_photo = State()

    required_channel_title = State()
    required_channel_chat_id = State()
    required_channel_invite_url = State()
