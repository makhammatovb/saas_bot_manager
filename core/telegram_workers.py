import asyncio
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.conf import settings

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PeerFloodError,
    UserPrivacyRestrictedError,
    UserNotMutualContactError,
    UserAlreadyParticipantError,
    UserChannelsTooMuchError,
    UsernameNotOccupiedError,
    UserIdInvalidError,
    ChatAdminRequiredError,
)
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest

from core.models import Company, Job

logger = logging.getLogger(__name__)

DELAY_SECONDS = 5
POLL_INTERVAL_SECONDS = 3



def _get_next_pending_job_sync(company):
    return (
        Job.objects.filter(company=company, status="pending")
        .order_by("created_at")
        .first()
    )


def _mark_job_sync(job_id, status, error=None, retry_after=None):
    Job.objects.filter(id=job_id).update(
        status=status,
        error=error,
        retry_after=retry_after,
    )


def _get_today_add_count_sync(company):
    today = timezone.now().date()
    return Job.objects.filter(
        company=company, job_type="add", status="done", created_at__date=today
    ).count()


get_next_pending_job = sync_to_async(_get_next_pending_job_sync)
mark_job = sync_to_async(_mark_job_sync)
get_today_add_count = sync_to_async(_get_today_add_count_sync)


async def resolve_user(client, ref: str):
    ref = ref.strip()
    if ref.startswith("@"):
        return await client.get_entity(ref)
    return await client.get_entity(int(ref))


async def resolve_group(client, group_telegram_id: int):
    return await client.get_entity(group_telegram_id)


async def do_add(client, job) -> tuple[str, str | None, datetime | None]:
    try:
        user_entity = await resolve_user(client, job.user_ref)
        group_entity = await resolve_group(client, job.group_telegram_id)
        try:
            await client(InviteToChannelRequest(group_entity, [user_entity]))
        except TypeError:
            await client(AddChatUserRequest(group_entity.id, user_entity, fwd_limit=10))
        return "done", None, None

    except FloodWaitError as e:
        retry_at = datetime.now(dt_timezone.utc) + timedelta(seconds=e.seconds)
        logger.warning("FloodWait %ss on job %s (company %s)", e.seconds, job.id, job.company_id)
        return "pending", f"FloodWaitError: wait {e.seconds}s", retry_at

    except PeerFloodError:
        retry_at = datetime.now(dt_timezone.utc) + timedelta(hours=6)
        return "pending", "PeerFloodError: account is being rate-limited by Telegram", retry_at

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


async def do_remove(client, job) -> tuple[str, str | None, datetime | None]:
    try:
        user_entity = await resolve_user(client, job.user_ref)
        group_entity = await resolve_group(client, job.group_telegram_id)
        await client.kick_participant(group_entity, user_entity)
        return "done", None, None
    except FloodWaitError as e:
        retry_at = datetime.now(dt_timezone.utc) + timedelta(seconds=e.seconds)
        return "pending", f"FloodWaitError: wait {e.seconds}s", retry_at
    except ChatAdminRequiredError:
        return "failed", "Userbot account is not an admin in this group", None
    except Exception as e:
        return "failed", f"Unexpected error: {e}", None


async def process_one(client, company, job):
    await mark_job(job.id, "in_progress")

    if job.job_type == "add":
        today_count = await get_today_add_count(company)
        if today_count >= company.get_daily_limit():
            tomorrow = (timezone.now() + timedelta(days=1)).replace(
                hour=0, minute=5, second=0, microsecond=0
            )
            await mark_job(
                job.id, "pending",
                error=f"Daily add limit ({company.get_daily_limit()}) reached, retrying tomorrow",
                retry_after=tomorrow,
            )
            logger.info("Daily add limit hit for %s. Job %s deferred.", company.name, job.id)
            return
        status, error, retry_after = await do_add(client, job)
    else:
        status, error, retry_after = await do_remove(client, job)

    await mark_job(job.id, status, error=error, retry_after=retry_after)
    logger.info(
        "[%s] Job %s (%s -> group %s): %s%s",
        company.name, job.id, job.user_ref, job.group_telegram_id, status,
        f" ({error})" if error else "",
    )


async def company_worker_loop(company):
    client = TelegramClient(company.session_name, company.api_id, company.api_hash)
    await client.start()
    logger.info("Userbot connected for company: %s", company.name)

    while True:
        try:
            job = await get_next_pending_job(company)
            if job is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            await process_one(client, company, job)
            await asyncio.sleep(DELAY_SECONDS)

        except Exception:
            logger.exception("Worker loop error for company %s — continuing", company.name)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def run_all():
    companies = await sync_to_async(list)(
        Company.objects.filter(is_active=True)
    )
    if not companies:
        logger.warning("No active companies with userbot credentials found.")
        return

    logger.info("Starting %d company userbot worker(s)...", len(companies))
    await asyncio.gather(*(company_worker_loop(c) for c in companies))
