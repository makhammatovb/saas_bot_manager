import asyncio
from django.core.management.base import BaseCommand
from bot.bot import start_bot


class Command(BaseCommand):
    help = "Runs the Telegram bot (polling mode)"

    def handle(self, *args, **options):
        asyncio.run(start_bot())