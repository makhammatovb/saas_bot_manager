import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from django.conf import settings

from .handlers import dp

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)

async def start_bot():
    logger.info("Telegram Bot starting...")
    await dp.start_polling(bot)