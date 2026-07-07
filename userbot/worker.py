import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UserPrivacyRestrictedError,
    UserNotMutualContactError,
    UserAlreadyParticipantError,
    PeerFloodError,
    UserChannelsTooMuchError,
    UsernameNotOccupiedError,
    UserIdInvalidError,
    ChatAdminRequiredError,
)
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest

import conf
from db.models import init_db
from db import queries

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TelegramClient(conf.SESSION_PATH, conf.API_ID, conf.API_HASH)


async def resolve_user(ref: str):
    """ref is either '@username' or a numeric telegram_id as string."""
    ref = ref.strip()
    if ref.startswith("@"):
        return await client.get_entity(ref)
    return await client.get_entity(int(ref))


async def resolve_group(group_telegram_id: int):
    return await client.get_entity(group_telegram_id)


async def do_add(job: dict) -> tuple[str, str | None, str | None]:
    """Returns (status, error, retry_after_iso)."""
    try:
        user_entity = await resolve_user(job["user_ref"])
        group_entity = await resolve_group(job["group_telegram_id"])
        try:
            # Works for channels/supergroups
            await client(InviteToChannelRequest(group_entity, [user_entity]))
        except TypeError:
            # Basic (non-super) group fallback
            await client(AddChatUserRequest(group_entity.id, user_entity, fwd_limit=10))
        queries.increment_today_add_count()
        return "done", None, None

    except FloodWaitError as e:
        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=e.seconds)).isoformat()
        logger.warning("FloodWait %ss on job %s — backing off.", e.seconds, job["id"])
        return "flood_wait", f"FloodWaitError: wait {e.seconds}s", retry_at

    except PeerFloodError:
        # Telegram's broader anti-spam trigger. Back off hard.
        retry_at = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        return "flood_wait", "PeerFloodError: account is being rate-limited by Telegram", retry_at

    except UserPrivacyRestrictedError:
        return "failed", "User's privacy settings block being added by this account", None
    except UserNotMutualContactError:
        return "failed", "User must be a mutual contact to be added this way", None
    except UserAlreadyParticipantError:
        return "done", "User was already in the group", None
    except UserChannelsTooMuchError:
        return "failed", "Target user has joined too many channels/groups", None
    except UsernameNotOccupiedError:
        return "failed", "Username not found", None
    except UserIdInvalidError:
        return "failed", "Could not resolve this user (userbot may need to see them first)", None
    except ChatAdminRequiredError:
        return "failed", "Userbot account is not an admin in this group", None
    except Exception as e:
        return "failed", f"Unexpected error: {e}", None


async def do_remove(job: dict) -> tuple[str, str | None, str | None]:
    try:
        user_entity = await resolve_user(job["user_ref"])
        group_entity = await resolve_group(job["group_telegram_id"])
        await client.kick_participant(group_entity, user_entity)
        return "done", None, None
    except FloodWaitError as e:
        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=e.seconds)).isoformat()
        return "flood_wait", f"FloodWaitError: wait {e.seconds}s", retry_at
    except ChatAdminRequiredError:
        return "failed", "Userbot account is not an admin in this group", None
    except Exception as e:
        return "failed", f"Unexpected error: {e}", None


async def process_one(job: dict) -> None:
    queries.mark_job(job["id"], "in_progress")

    if job["job_type"] == "add":
        if queries.get_today_add_count() >= conf.DAILY_ADD_LIMIT:
            # Push it back to pending for tomorrow rather than failing it.
            tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
                hour=0, minute=5, second=0, microsecond=0
            ).isoformat()
            queries.mark_job(job["id"], "pending", error="Daily add limit reached, retrying tomorrow", retry_after_iso=tomorrow)
            logger.info("Daily add limit hit (%s). Job %s deferred.", conf.DAILY_ADD_LIMIT, job["id"])
            return
        status, error, retry_after = await do_add(job)
    else:
        status, error, retry_after = await do_remove(job)

    queries.mark_job(job["id"], status, error=error, retry_after_iso=retry_after)
    logger.info("Job %s (%s -> group %s): %s%s", job["id"], job["user_ref"], job["group_telegram_id"], status,
                f" ({error})" if error else "")


async def worker_loop():
    delay_by_type = {"add": conf.ADD_DELAY_SECONDS, "remove": conf.REMOVE_DELAY_SECONDS}
    while True:
        job = queries.get_next_pending_job()
        if job is None:
            await asyncio.sleep(conf.POLL_INTERVAL_SECONDS)
            continue

        await process_one(job)
        await asyncio.sleep(delay_by_type[job["job_type"]])


async def main():
    init_db(conf.DATABASE_URL)
    await client.start()
    logger.info("Userbot connected. Worker loop starting.")
    await worker_loop()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
