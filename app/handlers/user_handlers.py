import os
import asyncio
import aiohttp
from io import BytesIO
from typing import Union
from random import randint
import logging

from aiogram import Bot, types, F, Router
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext

from app.FSM.states import GenStates
from app.services.api_calls import FusionBrainGenerator, ImageAnalyzer
from app.keyboards.inline import get_main_keyboard, get_styles_keyboard, get_radio_stations_keyboard, create_image_menu
from app.settings import BOT_NAME, BOT_DESCRIPTION, CREATOR_USERNAME, TEXT_MODEL, VISION_MODEL, IMAGE_STYLES, YOUR_SITE_URL, CREATOR_ID

logger = logging.getLogger(__name__)
user_router = Router()

user_data = {}
user_conversations = {}
active_generations = {}

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

async def save_temp_image(image_bytes: bytes) -> str:
    os.makedirs("temp_images", exist_ok=True)
    filename = f"temp_images/image_{randint(0, 100000)}.jpg"
    with open(filename, "wb") as f:
        f.write(image_bytes)
    return filename

@user_router.message(Command("start"))
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

@user_router.message(F.text == "🔄 Новый диалог")
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

@user_router.message(F.text == "ℹ️ Информация")
async def info_cmd(message: types.Message):
    await message.answer(
        f"✨ <b>{BOT_NAME} - Информация</b> ✨\n\n"
        f"Я - {BOT_NAME}, AI-ассистент, созданный для помощи и вдохновения.\n\n"
        "<b>🧠 Моя архитектура:</b>\n"
        f"- <b>Текстовая модель:</b> {TEXT_MODEL}\n"
        f"- <b>Визуальная модель:</b> {VISION_MODEL}\n"
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

@user_router.message(F.text == "🎨 Сгенерировать изображение")
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

@user_router.message(GenStates.waiting_for_image_prompt, F.text == "❌ Отмена")
async def cancel_image_generation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"🖌️ {BOT_NAME} отменил генерацию изображения.",
        reply_markup=get_main_keyboard()
    )

@user_router.message(GenStates.waiting_for_image_prompt)
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

@user_router.callback_query(GenStates.waiting_for_image_style, lambda c: c.data.startswith("style_"))
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

        if style == "DEFAULT":
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_style")]
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

@user_router.message(GenStates.waiting_for_custom_style)
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
    bot = context.bot
    if isinstance(context, types.CallbackQuery):
        message = context.message
        user_id = context.from_user.id
    else:
        message = context
        user_id = context.from_user.id

    try:
        data = await state.get_data()
        prompt = data.get("prompt", "")
        custom_style = data.get("custom_style", "")

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

@user_router.callback_query(GenStates.waiting_for_image_style, lambda c: c.data == "cancel_style")
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

@user_router.message(F.photo)
async def analyze_img(message: types.Message, bot: Bot):
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

@user_router.callback_query(lambda c: c.data == "similar")
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

@user_router.message(F.text == "📻 Стриминговое радио")
async def handle_streaming_radio(message: types.Message):
    await message.answer(
        f"📻 <b>{BOT_NAME} - Стриминговое радио</b>\n\n"
        "Выберите станцию из списка ниже:",
        parse_mode="HTML",
        reply_markup=get_radio_stations_keyboard()
    )

@user_router.callback_query(lambda c: c.data.startswith("stream_station_"))
async def handle_stream_station_selection(callback: CallbackQuery):
    try:
        await callback.answer()

        station_name = callback.data.replace("stream_station_", "")
        if station_name not in STREAMING_STATIONS:
            await callback.answer("Станция не найдена", show_alert=True)
            return

        station_url = STREAMING_STATIONS[station_name]

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="▶️ Открыть в плеере",
                url=station_url
            )],
            [types.InlineKeyboardButton(
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

@user_router.callback_query(lambda c: c.data == "station_list")
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

@user_router.callback_query(lambda c: c.data == "radio_main_menu")
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

@user_router.message()
async def handle_text_message(message: types.Message, bot: Bot):
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
