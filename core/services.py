from .models import Job, TelegramGroup, TelegramUser

def enqueue_push(company, group_telegram_id: int, requested_by: int):
    users = TelegramUser.objects.filter(company=company)
    count = 0
    for user in users:
        ref = f"@{user.username}" if user.username else str(user.telegram_id)
        Job.objects.create(
            company=company,
            job_type='add',
            user_ref=ref,
            group_telegram_id=group_telegram_id,
            requested_by=requested_by,
            status='pending'
        )
        count += 1
    return count


def enqueue_wipe(company, group_telegram_id: int, requested_by: int):
    users = TelegramUser.objects.filter(company=company)
    count = 0
    for user in users:
        ref = f"@{user.username}" if user.username else str(user.telegram_id)
        Job.objects.create(
            company=company,
            job_type='remove',
            user_ref=ref,
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
