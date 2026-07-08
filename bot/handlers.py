from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ChatMemberUpdated
from asgiref.sync import sync_to_async
import logging
from conf import settings
from core.models import CustomUser, Company, TelegramGroup
from core.services import register_group, enqueue_push, enqueue_wipe

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


@dp.my_chat_member()
async def on_bot_added_to_group(event: ChatMemberUpdated):
    if event.chat.type not in ("group", "supergroup"):
        return
    if event.new_chat_member.status != "administrator":
        return

    company = await sync_to_async(get_user_company_sync)(event.from_user.id)
    if not company:
        await bot.send_message(
            event.from_user.id,
            "❌ You are not registered as a manager in any company.\n"
            "Contact super admin to link your Telegram ID."
        )
        return

    group, created = await sync_to_async(register_group)(
        company=company,
        telegram_id=event.chat.id,
        title=event.chat.title,
    )
    if created:
        await bot.send_message(
            event.from_user.id,
            f"✅ Group <b>{event.chat.title}</b> has been auto-registered "
            f"under company: <b>{company.name}</b>"
        )
    else:
        await bot.send_message(
            event.from_user.id,
            f"Group <b>{event.chat.title}</b> was already registered."
        )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    company = await sync_to_async(get_user_company_sync)(user.id)

    if company:
        await message.reply(
            f"👋 Welcome, manager of <b>{company.name}</b>!\n\n"
            "Add me as <b>admin</b> to any group you want to manage with "
            "push/wipe — it'll be auto-registered under your company.\n\n"
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
