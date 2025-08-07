from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.settings import STREAMING_STATIONS, IMAGE_STYLES

async def create_image_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎨 Сгенерировать похожее", callback_data="similar")
    return builder.as_markup()

def get_radio_stations_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    stations = list(STREAMING_STATIONS.items())
    for i in range(0, len(stations), 2):
        row = []
        for j in range(2):
            if i + j < len(stations):
                name, url = stations[i + j]
                row.append(InlineKeyboardButton(
                    text=name,
                    callback_data=f"stream_station_{name}"
                ))
        if row:
            keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="radio_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🔄 Новый диалог")],
        [KeyboardButton(text="🎨 Сгенерировать изображение"), KeyboardButton(text="📻 Стриминговое радио")],
        [KeyboardButton(text="ℹ️ Информация")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_styles_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    for style in IMAGE_STYLES:
        keyboard.append([InlineKeyboardButton(
            text=style["title"],
            callback_data=f"style_{style['name']}"
        )])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_style")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
