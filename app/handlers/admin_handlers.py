import logging
from aiogram import Bot, types, F, Router

from app.settings import CREATOR_ID

admin_router = Router()
logger = logging.getLogger(__name__)

@admin_router.message(F.reply_to_message)
async def handle_creator_reply(message: types.Message, bot: Bot):
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
