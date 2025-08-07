import os
import json
import base64
import logging
import aiohttp
import asyncio
import time
from io import BytesIO
from typing import Optional, Dict, Union, List, Tuple
from random import randint

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# --- Инициализация ---
load_dotenv()

# Константы
CREATOR_ID = 5478018239  # ID Сергея
BOT_NAME = "InspoGen"
BOT_DESCRIPTION = "Ваш AI-ассистент для творчества и вдохновения"
TEXT_MODEL = "meta-llama/llama-3-70b-instruct"
VISION_MODEL = "meta-llama/llama-4-maverick"
YOUR_SITE_URL = "https://t.me/InspoGenBot"
CREATOR_USERNAME = "Robis_M"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Стили для генерации изображений
IMAGE_STYLES = [
    {"name": "DEFAULT", "title": "Стандартный", "titleEn": "Default"},
    {"name": "KANDINSKY", "title": "Кандинский", "titleEn": "Kandinsky"},
    {"name": "UHD", "title": "Детальное фото", "titleEn": "Ultra HD"},
    {"name": "ANIME", "title": "Аниме", "titleEn": "Anime"},
    {"name": "RENDER", "title": "3D Рендер", "titleEn": "3D Render"},
    {"name": "OIL", "title": "Масляная живопись", "titleEn": "Oil Painting"},
    {"name": "WATERCOLOR", "title": "Акварель", "titleEn": "Watercolor"}
]

# Стриминговые радиостанции
STREAMING_STATIONS = {
    "10's Dance": "https://radiorecord.hostingradio.ru/201096.aacp",
    "2-step": "https://radiorecord.hostingradio.ru/2step96.aacp",
    "60's Dance": "https://radiorecord.hostingradio.ru/cadillac96.aacp",
    "70's Dance": "https://radiorecord.hostingradio.ru/197096.aacp",
    "A State of Trance": "https://radiorecord.hostingradio.ru/asot96.aacp",
    "Afro House": "https://radiorecord.hostingradio.ru/afro96.aacp",
    "Ambient": "https://radiorecord.hostingradio.ru/ambient96.aacp",
    "Armin van Buuren": "https://radiorecord.hostingradio.ru/armin96.aacp",
    "Bass House": "https://radiorecord.hostingradio.ru/jackin96.aacp",
    "Beach Party": "https://radiorecord.hostingradio.ru/beach96.aacp",
    "Big Hits": "https://radiorecord.hostingradio.ru/bighits96.aacp",
    "Black Rap": "https://radiorecord.hostingradio.ru/yo96.aacp",
    "Breaks": "https://radiorecord.hostingradio.ru/brks96.aacp",
    "Chill House": "https://radiorecord.hostingradio.ru/chillhouse96.aacp",
    "Chill-Out": "https://radiorecord.hostingradio.ru/chil96.aacp",
    "Christmas": "https://radiorecord.hostingradio.ru/christmas96.aacp",
    "Christmas Chill": "https://radiorecord.hostingradio.ru/christmaschill96.aacp",
    "Complextro": "https://radiorecord.hostingradio.ru/complextro96.aacp",
    "D'n'B Classics": "https://radiorecord.hostingradio.ru/drumhits96.aacp",
    "Dancecore": "https://radiorecord.hostingradio.ru/dc96.aacp",
    "Darkside": "https://radiorecord.hostingradio.ru/darkside96.aacp",
    "David Guetta": "https://radiorecord.hostingradio.ru/guetta96.aacp",
    "Deep": "https://radiorecord.hostingradio.ru/deep96.aacp",
    "Disco/Funk": "https://radiorecord.hostingradio.ru/discofunk96.aacp",
    "DJ Gvozd": "https://radiorecord.hostingradio.ru/djgvozd96.aacp",
    "DJ Цветкоff": "https://radiorecord.hostingradio.ru/tsvetkov96.aacp",
    "Dream Dance": "https://radiorecord.hostingradio.ru/dream96.aacp",
    "Dream Pop": "https://radiorecord.hostingradio.ru/dreampop96.aacp",
    "Dubstep": "https://radiorecord.hostingradio.ru/dub96.aacp",
    "EDM": "https://radiorecord.hostingradio.ru/club96.aacp",
    "EDM Classics": "https://radiorecord.hostingradio.ru/edmhits96.aacp",
    "Electro": "https://radiorecord.hostingradio.ru/elect96.aacp",
    "Eurodance": "https://radiorecord.hostingradio.ru/eurodance96.aacp",
    "Feel": "https://radiorecord.hostingradio.ru/feel96.aacp",
    "Festivals": "https://radiorecord.hostingradio.ru/livedjsets96.aacp",
    "Future Bass": "https://radiorecord.hostingradio.ru/fbass96.aacp",
    "Future House": "https://radiorecord.hostingradio.ru/fut96.aacp",
    "Future Rave": "https://radiorecord.hostingradio.ru/futurerave96.aacp",
    "GOA/PSY": "https://radiorecord.hostingradio.ru/goa96.aacp",
    "Groove/Tribal": "https://radiorecord.hostingradio.ru/groovetribal96.aacp",
    "Hard Bass": "https://radiorecord.hostingradio.ru/hbass96.aacp",
    "Hardstyle": "https://radiorecord.hostingradio.ru/teo96.aacp",
    "House Classics": "https://radiorecord.hostingradio.ru/houseclss96.aacp",
    "House Hits": "https://radiorecord.hostingradio.ru/househits96.aacp",
    "Hypnotic": "https://radiorecord.hostingradio.ru/hypno96.aacp",
    "Innocence": "https://radiorecord.hostingradio.ru/inno96.aacp"
}

# Хранилища данных
user_data: Dict[int, Dict] = {}
user_conversations: Dict[int, List[Dict[str, str]]] = {}
active_generations: Dict[int, bool] = {}

# --- Состояния FSM ---
class GenStates(StatesGroup):
    waiting_for_image_prompt = State()
    waiting_for_image_style = State()
    waiting_for_custom_style = State()

# --- Класс для генерации изображений ---
class FusionBrainGenerator:
    def __init__(self):
        self.url = 'https://api-key.fusionbrain.ai/'
        self.headers = {
            'X-Key': f'Key {os.getenv("FUSIONBRAIN_API_KEY")}',
            'X-Secret': f'Secret {os.getenv("FUSIONBRAIN_SECRET_KEY")}',
        }
        self.pipeline_id = None

    async def get_pipeline(self) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url + 'key/api/v1/pipelines', headers=self.headers, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if not data:
                        logger.error("No available pipelines")
                        return None
                    self.pipeline_id = data[0]['id']
                    return self.pipeline_id
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return None

    async def generate(self, prompt: str, style: str = None) -> Optional[str]:
        try:
            if not self.pipeline_id:
                await self.get_pipeline()
                if not self.pipeline_id:
                    return None

            params = {
                "type": "GENERATE",
                "numImages": 1,
                "width": 1024,
                "height": 1024,
                "generateParams": {
                    "query": prompt[:1000]
                }
            }

            if style and style != "DEFAULT":
                params["style"] = style

            form_data = aiohttp.FormData()
            form_data.add_field('pipeline_id', self.pipeline_id)
            form_data.add_field('params', json.dumps(params, ensure_ascii=False), content_type='application/json')

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url + 'key/api/v1/pipeline/run',
                    headers=self.headers,
                    data=form_data,
                    timeout=30
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            if 'uuid' not in data:
                logger.error("No UUID in response")
                return None

            return data['uuid']

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return None

    async def check_generation(self, request_id: str, attempts: int = 15, delay: int = 5) -> Optional[Tuple[bytes, bool]]:
        try:
            while attempts > 0:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.url + 'key/api/v1/pipeline/status/' + request_id,
                        headers=self.headers,
                        timeout=10
                    ) as response:
                        data = await response.json()

                if data['status'] == 'DONE':
                    image_base64 = data['result']['files'][0]
                    censored = data['result'].get('censored', False)
                    return base64.b64decode(image_base64), censored
                elif data['status'] == 'FAIL':
                    error = data.get('errorDescription', 'Unknown error')
                    logger.error(f"Generation failed: {error}")
                    return None, False

                attempts -= 1
                await asyncio.sleep(delay)

            logger.error("Generation timeout")
            return None, False

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return None, False

# --- Класс для анализа изображений ---
class ImageAnalyzer:
    @staticmethod
    async def analyze(image_bytes: bytes, prompt: str = "Опиши изображение подробно на русском") -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                        'HTTP-Referer': YOUR_SITE_URL,
                        'X-Title': BOT_NAME,
                    },
                    json={
                        'model': VISION_MODEL,
                        'messages': [
                            {
                                'role': 'user',
                                'content': [
                                    {'type': 'text', 'text': prompt},
                                    {
                                        'type': 'image_url',
                                        'image_url': {
                                            'url': f'data:image/jpeg;base64,{base64.b64encode(image_bytes).decode("utf-8")}'
                                        }
                                    }
                                ]
                            }
                        ],
                        'max_tokens': 1000
                    },
                    timeout=30
                ) as response:
                    if response.status != 200:
                        data = await response.json()
                        error_msg = data.get('error', {}).get('message', 'Неизвестная ошибка API')
                        logger.error(f"Vision API Error: {error_msg}")
                        return f"❌ Ошибка анализа изображения: {error_msg}"

                    data = await response.json()
                    return data['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            return f"❌ Ошибка: {str(e)}"

# --- Вспомогательные функции ---
async def save_temp_image(image_bytes: bytes) -> str:
    os.makedirs("temp_images", exist_ok=True)
    filename = f"temp_images/image_{randint(0, 100000)}.jpg"
    with open(filename, "wb") as f:
        f.write(image_bytes)
    return filename

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

def add_message_to_history(user_id: int, role: str, content: str):
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    if len(user_conversations[user_id]) >= 10:
        user_conversations[user_id].pop(0)

    user_conversations[user_id].append({
        "role": role,
        "content": content
    })

def clear_user_history(user_id: int):
    if user_id in user_conversations:
        user_conversations[user_id] = []

# --- Обработчики сообщений ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    clear_user_history(message.from_user.id)
    await message.answer(
        f"✨ <b>{BOT_NAME} - {BOT_DESCRIPTION}</b>\n\n"
        "Я умею:\n"
        "- Отвечать на ваши вопросы (с сохранением контекста)\n"
        "- Анализировать изображения\n"
        "- Генерировать изображения по описанию\n"
        "- Предоставлять стриминговое радио\n\n"
        "Используйте кнопку <b>🔄 Новый диалог</b> чтобы очистить историю общения.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🔄 Новый диалог")
async def new_dialog(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    clear_user_history(user_id)
    if user_id in user_data:
        user_data[user_id] = {}
    await message.answer(
        f"🆕 {BOT_NAME} начал новый диалог. Предыдущая история очищена. Чем могу помочь?",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "ℹ️ Информация")
async def info_cmd(message: types.Message):
    await message.answer(
        f"✨ <b>{BOT_NAME} - Информация</b> ✨\n\n"
        f"Я - {BOT_NAME}, AI-ассистент, созданный для помощи и вдохновения.\n\n"
        "<b>🧠 Моя архитектура:</b>\n"
        "- <b>Текстовая модель:</b> LLaMA 3 70B (от Meta)\n"
        "- <b>Визуальная модель:</b> LLaMA 4 Maverick (от Meta)\n"
        "- <b>Генерация изображений:</b> Kandinsky 3.1\n\n"
        "<b>🔧 Техническая база:</b>\n"
        "- Fusion Brain API для генерации изображений\n"
        "- OpenRouter для доступа к AI-моделям\n"
        "- Aiogram 3.x для Telegram-интерфейса\n\n"
        "<b>💡 Особенности:</b>\n"
        "- Поддержка контекстного диалога\n"
        "- Мультимодальность (текст + изображения)\n"
        "- 7+ стилей генерации изображений\n"
        "- Стриминговое радио\n\n"
        f"👨‍💻 Создатель: @{CREATOR_USERNAME}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🎨 Сгенерировать изображение")
async def handle_generate_image(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if active_generations.get(user_id, False):
        await message.answer(
            "⏳ Пожалуйста, подождите! У вас уже идет процесс генерации изображения.",
            reply_markup=get_main_keyboard()
        )
        return

    await state.set_state(GenStates.waiting_for_image_prompt)
    await message.answer(
        f"🖌️ {BOT_NAME} может создать изображение по вашему описанию. "
        "Введите подробное описание того, что вы хотите увидеть:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )

@dp.message(GenStates.waiting_for_image_prompt, F.text == "❌ Отмена")
async def cancel_image_generation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"🖌️ {BOT_NAME} отменил генерацию изображения.",
        reply_markup=get_main_keyboard()
    )

@dp.message(GenStates.waiting_for_image_prompt)
async def handle_image_prompt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if active_generations.get(user_id, False):
        await message.answer(
            "⏳ Пожалуйста, подождите! У вас уже идет процесс генерации изображения.",
            reply_markup=get_main_keyboard()
        )
        return

    await state.update_data(prompt=message.text)
    await state.set_state(GenStates.waiting_for_image_style)
    await message.answer(
        "🖌️ Выберите стиль для генерации изображения:",
        reply_markup=get_styles_keyboard()
    )

@dp.callback_query(GenStates.waiting_for_image_style, lambda c: c.data.startswith("style_"))
async def handle_style_selection(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    try:
        await callback.answer()
    except:
        pass

    if active_generations.get(user_id, False):
        try:
            await callback.message.answer(
                "⏳ Пожалуйста, подождите! У вас уже идет процесс генерации изображения.",
                reply_markup=get_main_keyboard()
            )
        except:
            pass
        return

    try:
        style = callback.data.split("_")[1]
        user_data = await state.get_data()

        if style == "DEFAULT":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_style")]
            ])
            try:
                await callback.message.edit_text(
                    "🎨 Опишите желаемый стиль изображения (например: 'акварель, пастельные тона, легкая текстура бумаги'):",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await callback.message.answer(
                    "🎨 Опишите желаемый стиль изображения (например: 'акварель, пастельные тона, легкая текстура бумаги'):",
                    reply_markup=keyboard
                )
            await state.set_state(GenStates.waiting_for_custom_style)
            await state.update_data(style=style)
            return

        active_generations[user_id] = True
        await generate_image_with_style(callback, state, style)

    except Exception as e:
        logger.error(f"Error in handle_style_selection: {e}")
        active_generations.pop(user_id, None)

        try:
            await callback.message.answer(
                f"⚠️ {BOT_NAME} временно не может обработать запрос. Пожалуйста, попробуйте еще раз.",
                reply_markup=get_main_keyboard()
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

@dp.message(GenStates.waiting_for_custom_style)
async def handle_custom_style_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if active_generations.get(user_id, False):
        await message.answer(
            "⏳ Пожалуйста, подождите! У вас уже идет процесс генерации изображения.",
            reply_markup=get_main_keyboard()
        )
        return

    active_generations[user_id] = True
    custom_style = message.text
    await state.update_data(custom_style=custom_style)
    await generate_image_with_style(message, state, "DEFAULT")

async def generate_image_with_style(context: Union[types.Message, types.CallbackQuery], state: FSMContext, style: str):
    if isinstance(context, types.CallbackQuery):
        message = context.message
        user_id = context.from_user.id
    else:
        message = context
        user_id = context.from_user.id

    try:
        user_data = await state.get_data()
        prompt = user_data.get("prompt", "")
        custom_style = user_data.get("custom_style", "")

        full_prompt = prompt
        if style == "DEFAULT" and custom_style:
            full_prompt = f"{prompt}, стиль: {custom_style}"

        await bot.send_chat_action(message.chat.id, "upload_photo")

        try:
            msg = await message.answer(f"🖌️ {BOT_NAME} генерирует изображение... Это займет 15-30 секунд.")
        except Exception as e:
            logger.error(f"Failed to send generation message: {e}")
            msg = None

        api = FusionBrainGenerator()
        uuid = await api.generate(full_prompt, style=style if style != "DEFAULT" else None)

        if not uuid:
            error_msg = f"⚠️ {BOT_NAME} не смог начать генерацию. Попробуйте позже."
            if msg:
                try:
                    await msg.edit_text(error_msg)
                except:
                    await message.answer(error_msg)
            else:
                await message.answer(error_msg)
            return

        image_bytes, censored = await api.check_generation(uuid)

        if not image_bytes:
            error_msg = f"⚠️ {BOT_NAME} не смог создать изображение. Попробуйте другой запрос."
            if msg:
                try:
                    await msg.edit_text(error_msg)
                except:
                    await message.answer(error_msg)
            else:
                await message.answer(error_msg)
            return

        if censored:
            error_msg = "⚠️ Запрос был отклонен системой модерации. Пожалуйста, измените описание."
            if msg:
                try:
                    await msg.edit_text(error_msg)
                except:
                    await message.answer(error_msg)
            else:
                await message.answer(error_msg)
            return

        filename = await save_temp_image(image_bytes)
        style_title = next((s["title"] for s in IMAGE_STYLES if s["name"] == style), "Стандартный")

        caption = f"🖼️ {BOT_NAME} создал изображение по запросу: {prompt}\nСтиль: {style_title}"
        if style == "DEFAULT" and custom_style:
            caption += f" ({custom_style})"

        await message.answer_photo(
            FSInputFile(filename),
            caption=caption,
            reply_markup=get_main_keyboard()
        )

        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["last_prompt"] = full_prompt

        try:
            os.remove(filename)
        except Exception as e:
            logger.error(f"Ошибка при удалении файла: {e}")

        if msg:
            try:
                await msg.delete()
            except:
                pass

    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        error_msg = f"⚠️ {BOT_NAME} столкнулся с ошибкой: {str(e)}"
        try:
            await message.answer(error_msg, reply_markup=get_main_keyboard())
        except:
            pass

    finally:
        active_generations.pop(user_id, None)
        await state.clear()

@dp.callback_query(GenStates.waiting_for_image_style, lambda c: c.data == "cancel_style")
async def handle_cancel_style(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except:
        pass

    await state.clear()
    try:
        await callback.message.edit_text(f"🖌️ {BOT_NAME} отменил генерацию изображения.")
    except:
        await callback.message.answer(f"🖌️ {BOT_NAME} отменил генерацию изображения.")

@dp.message(F.photo)
async def analyze_img(message: types.Message):
    try:
        msg = await message.answer(f"🔍 {BOT_NAME} анализирует изображение...")

        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)

        caption = message.caption if message.caption else "Опиши это изображение подробно"
        analysis = await ImageAnalyzer.analyze(file_bytes.read(), caption)

        user_id = message.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {}

        user_data[user_id]["last_analysis"] = analysis

        await msg.edit_text(
            f"📝 {BOT_NAME} проанализировал изображение:\n\n{analysis}",
            reply_markup=await create_image_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {e}")
        try:
            await msg.edit_text(f"❌ {BOT_NAME} не смог проанализировать изображение: {str(e)}")
        except:
            await message.answer(f"❌ {BOT_NAME} не смог проанализировать изображение: {str(e)}")

@dp.callback_query(lambda c: c.data == "similar")
async def generate_similar_img(callback: CallbackQuery):
    user_id = callback.from_user.id

    if active_generations.get(user_id, False):
        try:
            await callback.answer("⏳ Пожалуйста, подождите! У вас уже идет процесс генерации изображения.", show_alert=True)
        except:
            pass
        return

    if user_id not in user_data or "last_analysis" not in user_data[user_id]:
        try:
            await callback.answer(f"❌ {BOT_NAME}: сначала загрузите изображение", show_alert=True)
        except:
            pass
        return

    active_generations[user_id] = True

    try:
        await callback.answer()

        analysis = user_data[user_id]["last_analysis"]
        clean_analysis = analysis[:500].replace('|', '').replace('\\', '')
        prompt = f"Создай изображение похожее на: {clean_analysis}"

        msg = await callback.message.answer(f"🎨 {BOT_NAME} создает похожее изображение...")

        try:
            api = FusionBrainGenerator()
            uuid = await api.generate(prompt)

            if not uuid:
                await msg.edit_text(f"❌ {BOT_NAME} не смог начать генерацию")
                return

            image_bytes, censored = await api.check_generation(uuid)

            if image_bytes:
                filename = await save_temp_image(image_bytes)
                try:
                    await callback.message.answer_photo(
                        FSInputFile(filename),
                        caption=f"🖼️ {BOT_NAME} создал похожее изображение",
                        reply_markup=get_main_keyboard()
                    )
                    await msg.delete()
                finally:
                    try:
                        os.remove(filename)
                    except:
                        pass
            else:
                await msg.edit_text(f"❌ {BOT_NAME} не смог создать изображение")
        except Exception as e:
            logger.error(f"Ошибка генерации похожего изображения: {e}")
            await msg.edit_text(f"❌ {BOT_NAME} столкнулся с ошибкой при генерации")

    except Exception as e:
        logger.error(f"Ошибка в generate_similar_img: {e}")

    finally:
        active_generations.pop(user_id, None)

# --- Обработчики для стримингового радио ---
@dp.message(F.text == "📻 Стриминговое радио")
async def handle_streaming_radio(message: types.Message):
    await message.answer(
        f"📻 <b>{BOT_NAME} - Стриминговое радио</b>\n\n"
        "Выберите станцию из списка ниже:",
        parse_mode="HTML",
        reply_markup=get_radio_stations_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("stream_station_"))
async def handle_stream_station_selection(callback: CallbackQuery):
    try:
        await callback.answer()

        station_name = callback.data.replace("stream_station_", "")
        if station_name not in STREAMING_STATIONS:
            await callback.answer("Станция не найдена", show_alert=True)
            return

        station_url = STREAMING_STATIONS[station_name]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="▶️ Открыть в плеере",
                url=station_url
            )],
            [InlineKeyboardButton(
                text="📻 Выбрать другую станцию",
                callback_data="station_list"
            )]
        ])

        await callback.message.edit_text(
            f"🎧 {BOT_NAME} выбрал станцию: <b>{station_name}</b>\n"
            "Нажмите кнопку ниже, чтобы открыть в аудиоплеере",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора станции: {str(e)}")
        try:
            await callback.answer(f"{BOT_NAME} временно не может обработать запрос. Пожалуйста, попробуйте еще раз.", show_alert=True)
        except:
            pass

@dp.callback_query(lambda c: c.data == "station_list")
async def handle_station_list_callback(callback: CallbackQuery):
    try:
        await callback.answer()
        await callback.message.edit_text(
            f"📻 <b>{BOT_NAME} - Стриминговое радио</b>\n\n"
            "Выберите станцию из списка ниже:",
            parse_mode="HTML",
            reply_markup=get_radio_stations_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при отображении списка станций: {str(e)}")
        try:
            await callback.answer(f"{BOT_NAME} временно не может показать список станций. Пожалуйста, попробуйте еще раз.", show_alert=True)
        except:
            pass

@dp.callback_query(lambda c: c.data == "radio_main_menu")
async def handle_radio_main_menu(callback: CallbackQuery):
    try:
        await callback.answer()
        await callback.message.delete()
        await callback.message.answer(
            f"Главное меню {BOT_NAME}:",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {str(e)}")
        try:
            await callback.answer(f"{BOT_NAME} временно не может вернуться в главное меню. Пожалуйста, попробуйте еще раз.", show_alert=True)
        except:
            pass

# --- Обработчики для сообщений создателю ---
@dp.message()
async def handle_text_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower()

    # Проверка на сообщение для создателя
    creator_keywords = [
        "сергей", "серёжа", "создатель", "разработчик",
        "автор", "developer", "создателю", "Сергею", "Сереже", "Передай", "Передай привет", "Передай ему привет",
        "Спроси у"
    ]

    if any(keyword in text for keyword in creator_keywords) and (
        "привет" in text or "передай" in text or "скажи" in text or "спроси" in text
    ):
        user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        message_to_creator = (
            f"Серёга, привет 👋 \n\n"
            f"Пользователь {user_name} (ID: {user_id}) пишет📩:\n\n"
            f"{message.text}\n\n"
        )

        try:
            await bot.send_message(
                chat_id=CREATOR_ID,
                text=message_to_creator
            )
            await message.answer("Ваше сообщение отправлено создателю InspoGen ✅ ")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения создателю: {e}")
            await message.answer("❌ Не удалось отправить сообщение создателю. Попробуйте позже.")
        return

    # Проверяем, не идет ли генерация изображения
    if active_generations.get(user_id, False):
        await message.answer(
            "⏳ Пожалуйста, подожди! Сейчас идет процесс генерации изображения. Я отвечу тебе сразу после его завершения.",
            reply_markup=get_main_keyboard()
        )
        return

    # Добавляем сообщение пользователя в историю
    add_message_to_history(user_id, "user", message.text)

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Получаем историю диалога для контекста
        conversation_history = user_conversations.get(user_id, [])

        # Используем OpenRouter API для ответов с историей диалога
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "HTTP-Referer": YOUR_SITE_URL,
                    "X-Title": BOT_NAME,
                },
                json={
                    "model": TEXT_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Ты - {BOT_NAME}, дружелюбный и полезный AI-ассистент. "
                                      f"Ты был создан Сергеем как мультимодальный AI помощник. "
                                      "Ты объединяешь несколько нейросетевых моделей:\n"
                                      f"- Текстовая модель: {TEXT_MODEL}\n"
                                      f"- Визуальная модель: {VISION_MODEL}\n"
                                      "- Kandinsky 3.1 для генерации изображений\n\n"
                                      "Отвечай кратко, информативно и по делу. "
                                      "Если пользователь спрашивает кто тебя создал, отвечай что Сергей."
                                      "Отвечай всегда на русском языке"
                        },
                        *conversation_history
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=20
            ) as response:
                if response.status != 200:
                    data = await response.json()
                    error_msg = data.get("error", {}).get("message", "Неизвестная ошибка API")
                    logger.error(f"API Error: {error_msg}")
                    await message.answer(f"🔧 {BOT_NAME} временно недоступен. Попробуй позже.")
                    return

                data = await response.json()
                answer = data["choices"][0]["message"]["content"]

        # Добавляем ответ ассистента в историю
        add_message_to_history(user_id, "assistant", answer)

        await message.answer(answer[:4000], reply_markup=get_main_keyboard())

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await message.answer(f"⚠️ {BOT_NAME} временно не может ответить. Пожалуйста, попробуй позже.")

@dp.message(F.reply_to_message)
async def handle_creator_reply(message: types.Message):
    """Обработка ответов от создателя"""
    if message.from_user.id != CREATOR_ID:
        return

    try:
        # Парсим оригинальное сообщение бота
        original_text = message.reply_to_message.text

        # Ищем ID пользователя в сообщении
        if "(ID:" not in original_text:
            return

        user_id = int(original_text.split("(ID:")[1].split(")")[0].strip())
        reply_text = f"🔹 Ответ от создателя:\n\n{message.text}"

        await bot.send_message(
            chat_id=user_id,
            text=reply_text
        )
        await message.answer("✅ Ответ успешно отправлен пользователю")

    except Exception as e:
        logger.error(f"Ошибка обработки ответа создателя: {e}")
        await message.answer("❌ Не удалось отправить ответ пользователю")

# --- Запуск ---
async def main():
    logger.info(f"🟢 {BOT_NAME} успешно запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
