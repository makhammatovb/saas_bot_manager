import asyncio
import logging
from django.conf import settings

from .handlers import dp, bot

logger = logging.getLogger(__name__)


async def start_bot():
    logger.info("Telegram Bot starting...")
    await dp.start_polling(bot)