from aiogram.fsm.state import State, StatesGroup


class AdminFlow(StatesGroup):
    news_title = State()
    news_body = State()
    broadcast_text = State()
