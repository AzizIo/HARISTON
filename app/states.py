from aiogram.fsm.state import State, StatesGroup


class AdminFlow(StatesGroup):
    news_title = State()
    news_body = State()
    broadcast_text = State()
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
