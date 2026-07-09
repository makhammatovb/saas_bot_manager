from .models import Job, TelegramGroup, TelegramUser


def build_user_ref(user: TelegramUser) -> str:
    if user.username:
        username = user.username.strip()
        return username if username.startswith("@") else f"@{username}"
    return str(user.telegram_id)


def _get_target_users(company, user_ids=None):
    users = TelegramUser.objects.filter(company=company)
    if user_ids:
        users = users.filter(id__in=user_ids)
    return users


def enqueue_push(company, group_telegram_id: int, requested_by: int, user_ids=None):
    users = _get_target_users(company, user_ids)
    count = 0
    for user in users:
        Job.objects.create(
            company=company,
            job_type='add',
            user_ref=build_user_ref(user),
            group_telegram_id=group_telegram_id,
            requested_by=requested_by,
            status='pending'
        )
        count += 1
    return count


def enqueue_wipe(company, group_telegram_id: int, requested_by: int, user_ids=None):
    users = _get_target_users(company, user_ids)
    count = 0
    for user in users:
        Job.objects.create(
            company=company,
            job_type='remove',
            user_ref=build_user_ref(user),
            group_telegram_id=group_telegram_id,
            requested_by=requested_by,
            status='pending'
        )
        count += 1
    return count


def register_group(company, telegram_id, title):
    group, created = TelegramGroup.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "title": title,
            "company": company,
        },
    )
    return group, created
