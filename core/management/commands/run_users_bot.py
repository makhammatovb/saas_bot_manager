import asyncio
from django.core.management.base import BaseCommand
from core.telegram_workers import run_all


class Command(BaseCommand):
    help = "Runs all active companies' userbot workers (one Telethon client each, concurrently)"

    def handle(self, *args, **options):
        asyncio.run(run_all())
        