from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from asgiref.sync import sync_to_async
import logging
from conf import settings
from core.models import CustomUser

logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


def get_user_company_sync(telegram_id: int):
    try:
        user = CustomUser.objects.select_related('company').get(telegram_id=telegram_id)
        return user.company if user.company else None
    except CustomUser.DoesNotExist:
        return None


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    company = await sync_to_async(get_user_company_sync)(user.id)

    if company:
        await message.reply(
            f"👋 Welcome, manager of <b>{company.name}</b>!\n\n"
            "Add your company's userbot account as <b>admin</b> to any group "
            "you want to manage with push/wipe — it'll be auto-registered "
            "under your company automatically.\n\n"
            "Use the web dashboard for full management. "
            "You can still use some commands here."
        )
    else:
        username_line = f"@{user.username}" if user.username else "(no username set)"
        await message.reply(
            "👋 Hi! You're not registered as a company manager yet.\n\n"
            f"Your Telegram ID: <code>{user.id}</code>\n"
            f"Your username: {username_line}\n\n"
            "Send this info to your company manager so they can add you "
            "to the managed user list."
        )
