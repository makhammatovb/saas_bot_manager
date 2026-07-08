from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from asgiref.sync import sync_to_async
import logging
from conf import settings
from core.models import CustomUser, Company, TelegramGroup
from core.services import register_group, enqueue_push, enqueue_wipe

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
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
        added_by_bot=True
    )
    if created:
        await bot.send_message(
            event.from_user.id,
            f"✅ Group **{event.chat.title}** has been auto-registered "
            f"under company: **{company.name}**"
        )
    else:
        await bot.send_message(
            event.from_user.id,
            f"Group **{event.chat.title}** was already registered."
        )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    company = await sync_to_async(get_user_company_sync)(user.id)
    if company:
        await message.reply(
            f"👋 Welcome, manager of **{company.name}**!\n\n"
            "Use the web dashboard for full management.\n"
            "You can still use some commands here."
        )
    else:
        await message.reply(
            "👋 Hi! Send your Telegram ID to super admin to be registered as company manager."
        )
