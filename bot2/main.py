import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated

import conf
from db.models import init_db
from db import queries

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=conf.BOT_TOKEN)
dp = Dispatcher()


def is_admin(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id in conf.ADMIN_IDS


async def deny(message: Message):
    await message.reply("You're not authorized to use this bot.")


async def notify_admins(text: str) -> None:
    for admin_id in conf.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logger.warning("Could not notify admin %s: %s", admin_id, e)


@dp.my_chat_member()
async def on_bot_membership_change(event: ChatMemberUpdated):
    if event.chat.type not in ("group", "supergroup"):
        return
    if event.new_chat_member.status != "administrator":
        return

    ok, msg = queries.add_group(event.chat.id, event.chat.title)
    if ok:
        await notify_admins(
            f"Bot was made admin in \"{event.chat.title}\" (id: {event.chat.id}).\n"
            f"Group auto-registered. Remember: the userbot account also needs "
            f"to join this group (ideally as admin) before /push or /wipe will work here."
        )
    else:
        logger.info("Bot promoted to admin in already-registered group %s: %s", event.chat.id, msg)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message):
        user = message.from_user
        username_line = f"@{user.username}" if user.username else "(no username set)"
        return await message.reply(
            "👋 Hi! This bot manages access to some group chats.\n\n"
            f"Your Telegram ID: {user.id}\n"
            f"Your username: {username_line}\n\n"
            "Please send this ID (or your username, if you have one) to the "
            "admin so they can add you to the managed list."
        )
    await message.reply(
        "Group membership manager ready.\n\n"
        "/adduser <username or numeric id>\n"
        "/removeuser <username or numeric id>\n"
        "/listusers\n"
        "/addgroup <group_id> <title>\n"
        "/removegroup <group_id>\n"
        "/listgroups\n"
        "/push <group_id>  - add all listed users to this group\n"
        "/wipe <group_id>  - remove all listed users from this group\n"
        "/status"
    )


@dp.message(Command("adduser"))
async def cmd_adduser(message: Message):
    if not is_admin(message):
        return await deny(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /adduser <username or numeric id>")
    ok, msg = queries.add_user(identifier=parts[1].strip(), added_by=message.from_user.id)
    await message.reply(msg)


@dp.message(Command("removeuser"))
async def cmd_removeuser(message: Message):
    if not is_admin(message):
        return await deny(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /removeuser <username or numeric id>")
    ok, msg = queries.remove_user(identifier=parts[1].strip())
    await message.reply(msg)


@dp.message(Command("listusers"))
async def cmd_listusers(message: Message):
    if not is_admin(message):
        return await deny(message)
    users = queries.list_users()
    if not users:
        return await message.reply("Managed list is empty.")
    lines = [f"- @{u['username']}" if u["username"] else f"- id {u['telegram_id']}" for u in users]
    await message.reply("Managed users:\n" + "\n".join(lines))


@dp.message(Command("addgroup"))
async def cmd_addgroup(message: Message):
    if not is_admin(message):
        return await deny(message)
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        return await message.reply("Usage: /addgroup <group_id> [title]")
    try:
        group_id = int(parts[1])
    except ValueError:
        return await message.reply("group_id must be numeric, e.g. -1001234567890")
    title = parts[2] if len(parts) > 2 else None
    ok, msg = queries.add_group(group_id, title)
    await message.reply(msg)


@dp.message(Command("removegroup"))
async def cmd_removegroup(message: Message):
    if not is_admin(message):
        return await deny(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /removegroup <group_id>")
    try:
        group_id = int(parts[1])
    except ValueError:
        return await message.reply("group_id must be numeric.")
    ok, msg = queries.remove_group(group_id)
    await message.reply(msg)


@dp.message(Command("listgroups"))
async def cmd_listgroups(message: Message):
    if not is_admin(message):
        return await deny(message)
    groups = queries.list_groups()
    if not groups:
        return await message.reply("No groups registered.")
    lines = [f"- {g['title'] or ''} ({g['telegram_id']})" for g in groups]
    await message.reply("Registered groups:\n" + "\n".join(lines))


@dp.message(Command("push"))
async def cmd_push(message: Message):
    if not is_admin(message):
        return await deny(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /push <group_id>")
    try:
        group_id = int(parts[1])
    except ValueError:
        return await message.reply("group_id must be numeric.")
    count = queries.enqueue_add_all_users_to_group(group_id, requested_by=message.from_user.id)
    await message.reply(
        f"Queued {count} add-jobs for group {group_id}.\n"
        f"The userbot worker will process these with a "
        f"{conf.ADD_DELAY_SECONDS}s delay between each, capped at "
        f"{conf.DAILY_ADD_LIMIT}/day. Use /status to track progress."
    )


@dp.message(Command("wipe"))
async def cmd_wipe(message: Message):
    if not is_admin(message):
        return await deny(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /wipe <group_id>")
    try:
        group_id = int(parts[1])
    except ValueError:
        return await message.reply("group_id must be numeric.")
    count = queries.enqueue_remove_all_users_from_group(group_id, requested_by=message.from_user.id)
    await message.reply(f"Queued {count} remove-jobs for group {group_id}. Use /status to track progress.")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin(message):
        return await deny(message)
    counts = queries.job_counts()
    today = queries.get_today_add_count()
    lines = [f"- {status}: {n}" for status, n in counts.items()] or ["- no jobs yet"]
    await message.reply(
        "Job queue:\n" + "\n".join(lines) +
        f"\n\nAdds performed today: {today}/{conf.DAILY_ADD_LIMIT}"
    )


async def main():
    init_db(conf.DATABASE_URL)
    logger.info("Bot starting (polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
