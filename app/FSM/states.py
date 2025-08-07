from aiogram.fsm.state import State, StatesGroup

class GenStates(StatesGroup):
    waiting_for_image_prompt = State()
    waiting_for_image_style = State()
    waiting_for_custom_style = State()
